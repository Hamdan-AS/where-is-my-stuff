"""Domain probes of supported matching boundaries, without production changes."""
import itertools
import math
import random
from datetime import timedelta
from django.test import SimpleTestCase
from django.utils import timezone
from core.forms import MatchingForm, LocationForm
from core.models import Report
from core.services import score, haversine_km


class DomainBoundaryTests(SimpleTestCase):
    def report(self, owner, kind, answers):
        return Report(owner_id=owner, kind=kind, status='Open', category='Bag',
            description='Blue fabric backpack', event_date=timezone.localdate(),
            lat=24.934, lng=67.112, answers=answers)

    def test_geographic_extremes_and_antipodal_rounding(self):
        rng = random.Random(22)
        coords = [(a,b) for a in (-90,0,90) for b in (-180,0,180)]
        for (a,b),(c,d) in itertools.product(coords,repeat=2):
            distance = haversine_km(a,b,c,d)
            self.assertTrue(math.isfinite(distance))
            self.assertGreaterEqual(distance,0)
            self.assertLessEqual(distance, math.pi*6371)
        for _ in range(10000):
            a,b = round(rng.uniform(-89,89),8),round(rng.uniform(-179,0),8)
            distance = haversine_km(a,b,-a,round(b+180,8))
            self.assertAlmostEqual(distance,math.pi*6371,delta=.001)

    def test_location_form_numeric_extremes(self):
        base = dict(location='Library', location_detail='Main entrance')
        for lat,lng in [('-90','-180'),('90','180'),('0','0')]:
            form = LocationForm({**base,'lat':lat,'lng':lng})
            self.assertTrue(form.is_valid(),form.errors)
        for lat,lng in [('90.00000001','0'),('0','180.00000001'),('NaN','0'),('0','Infinity')]:
            form = LocationForm({**base,'lat':lat,'lng':lng})
            self.assertFalse(form.is_valid())

    def test_date_score_bands_and_eligibility(self):
        answers = dict(colour='Blue',kind='Backpack',material='Fabric',pockets='2',mark='None')
        left,right = self.report(1,'Lost',answers),self.report(2,'Found',answers)
        for days, expected in [(0,15),(1,10),(-1,10),(2,5),(3,5),(4,0)]:
            right.event_date = left.event_date+timedelta(days=days)
            self.assertEqual(score(left,right)[1]['Date'],expected)
        for attr,value in [('status','Returned'),('owner_id',1),('kind','Lost'),('category','Keys')]:
            right = self.report(2,'Found',answers)
            setattr(right,attr,value)
            self.assertIsNone(score(left,right))

    def test_all_five_card_order_permutations(self):
        base = dict(colour='Black',material='Leather',logo='No',contents=['Bank cards'],bank_count=5,mark='None')
        cards = [('HBL','4111111111111111'),('MCB','4222222222222222'),('UBL','4333333333333333'),('NayaPay','4444444444444444'),('Other','4555555555555555')]
        def answers(order):
            data = dict(base)
            for i,(issuer,number) in enumerate(order,1):
                data.update({f'bank_{i}_issuer':issuer,f'bank_{i}_suffix':number})
                if issuer == 'Other':
                    data[f'bank_{i}_other']='Example Bank'
            form=MatchingForm(data,category='Wallet / Purse',selection=data)
            self.assertTrue(form.is_valid(),form.errors)
            return form.cleaned_data
        left=self.report(1,'Lost',answers(cards))
        for order in itertools.permutations(cards):
            right=self.report(2,'Found',answers(order))
            left.category=right.category='Wallet / Purse'
            self.assertEqual(score(left,right)[0],100)

    def test_generic_values_do_not_supply_two_agreements(self):
        data=dict(colour='Other',kind='Other',mark='Other')
        left,right=self.report(1,'Lost',data),self.report(2,'Found',data)
        self.assertIsNone(score(left,right))
        left.answers=right.answers={**data,'colour':'Blue'}
        self.assertIsNone(score(left,right))
