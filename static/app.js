const form = document.querySelector('[data-report-form]');
if (form) {
  form.querySelectorAll('input[inputmode="numeric"]').forEach(input => {
    input.addEventListener('input', () => { input.value = input.value.replace(/[^0-9]/g, ''); });
  });
  form.addEventListener('invalid', event => {
    const field = event.target.closest('.field');
    if (field) field.classList.add('has-error');
  }, true);
  const refresh = form.querySelector('button[value="refresh"]');
  if (refresh) {
    ['contents', 'bank_count', 'logo', 'card_type'].forEach(name => {
      form.querySelectorAll('[name="' + name + '"]').forEach(field => {
        field.addEventListener('change', () => form.requestSubmit(refresh));
      });
    });
    refresh.hidden = true;
    document.getElementById('selection-help').textContent = 'Questions update when your selections change. Save and next keeps completed answers.';
  }
  const description = form.querySelector('[name="description"]');
  const hint = document.getElementById('privacy-hint');
  if (description && hint) {
    const inspect = () => {
      const risk = /[\w.+-]+@[\w.-]+\.[a-z]{2,}|(?:\d[ -]?){10,}|\b(?:cnic|nic|card|account|last .*digits)\b[^.\n]{0,80}\d/i.test(description.value);
      hint.textContent = risk ? 'Possible private information: remove contact details and identifiers before continuing.' : 'Use visible features such as colour, brand, and distinguishing marks.';
      hint.hidden = !risk;
      hint.style.color = risk ? '#b12b39' : '';
      description.setCustomValidity(risk ? 'Remove private information from the public description.' : '');
    };
    description.addEventListener('input', inspect);
    inspect();
  }

  const photoInput = form.querySelector('[name="photo"]');
  const photoPreview = form.querySelector('[data-photo-preview]');
  const photoPreviewImage = photoPreview && photoPreview.querySelector('[data-photo-preview-image]');
  const photoPreviewName = photoPreview && photoPreview.querySelector('[data-photo-preview-name]');
  const existingPhoto = form.querySelector('.existing-photo');
  const removePhoto = form.querySelector('[name="remove_photo"]');
  let photoPreviewUrl = null;
  const updatePhotoSelection = () => {
    const selected = photoInput && photoInput.files && photoInput.files[0];
    if (photoPreview) photoPreview.hidden = !selected;
    if (selected && photoPreviewImage) {
      if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl);
      photoPreviewUrl = URL.createObjectURL(selected);
      photoPreviewImage.src = photoPreviewUrl;
      photoPreviewImage.alt = 'Preview of ' + selected.name;
      if (photoPreviewName) photoPreviewName.textContent = selected.name;
    }
    if (selected && removePhoto) removePhoto.checked = false;
    if (existingPhoto) existingPhoto.hidden = Boolean(selected || (removePhoto && removePhoto.checked));
  };
  if (photoInput && photoPreview) {
    photoInput.addEventListener('change', updatePhotoSelection);
    if (removePhoto) removePhoto.addEventListener('change', updatePhotoSelection);
    window.addEventListener('pagehide', () => {
      if (photoPreviewUrl) URL.revokeObjectURL(photoPreviewUrl);
    }, { once: true });
  }
}

const picker = document.querySelector('[data-coords-picker]');
if (picker && typeof L !== 'undefined') {
  // Leaflet's own path heuristic returns a CSS-relative path, which it then
  // assigns to img.src. The browser resolves that against the page, not the
  // stylesheet, so on /drafts/<pk>/ the marker would load from
  // /drafts/<pk>/images/ and 404. Derive the directory from the leaflet.css
  // href so the icon resolves at any page depth and under any STATIC_URL.
  const leafletCss = document.querySelector('link[href*="leaflet.css"]');
  if (leafletCss) L.Icon.Default.imagePath = leafletCss.href.replace(/leaflet\.css(\?.*)?$/, 'images/');
  const mapEl = picker.querySelector('[data-coords-map]');
  const latInput = document.getElementById('id_lat');
  const lngInput = document.getElementById('id_lng');
  const statusEl = picker.querySelector('[data-map-status]');
  const savedLat = latInput ? parseFloat(latInput.value) : NaN;
  const savedLng = lngInput ? parseFloat(lngInput.value) : NaN;
  const saved = !isNaN(savedLat) && !isNaN(savedLng) && Math.abs(savedLat) <= 90 && Math.abs(savedLng) <= 180;
  const position = saved ? [savedLat, savedLng] : [24.8607, 67.0011];
  const map = L.map(mapEl).setView(position, saved ? 15 : 13);
  // Recalculate tiles and pin placement when the available layout width changes.
  const mapResize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
  mapResize.observe(mapEl);
  window.addEventListener('pagehide', () => mapResize.disconnect(), { once: true });
  L.tileLayer('https://tile.openstreetmap.de/{z}/{x}/{y}.png', {
    maxZoom: 18,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  // With no saved coordinates there is no pin, only a map centred on the city.
  // A pin sitting at the default centre would read as a placed location when
  // the form has no coordinates at all.
  const tip = { permanent: true, direction: 'top', offset: [0, -32], interactive: false, className: 'coords-tip' };
  let marker = null;
  const setCoords = (lat, lng, label) => {
    if (latInput) latInput.value = lat.toFixed(6);
    if (lngInput) lngInput.value = lng.toFixed(6);
    if (statusEl) statusEl.textContent = label;
    if (marker) marker.setTooltipContent(lat.toFixed(6) + ', ' + lng.toFixed(6));
  };
  // 'move' fires continuously while dragging, so the inputs and the pin label
  // track the pointer instead of only updating when the drag ends.
  const placePin = (latlng) => {
    if (!marker) {
      marker = L.marker(latlng, { draggable: true }).addTo(map).bindTooltip('', tip);
      marker.on('move', (event) => setCoords(event.latlng.lat, event.latlng.lng, 'Pin set. Drag to adjust.'));
    }
    marker.setLatLng(latlng);
  };
  if (saved) placePin(position);
  map.on('click', (event) => {
    placePin(event.latlng);
    setCoords(event.latlng.lat, event.latlng.lng, 'Pin set from map click.');
  });
  if (saved) setCoords(savedLat, savedLng, 'Pin loaded from your saved draft.');
  const locateButton = document.getElementById('use-current-location');
  if (locateButton && navigator.geolocation) {
    locateButton.addEventListener('click', () => {
      navigator.geolocation.getCurrentPosition((fix) => {
        const here = [fix.coords.latitude, fix.coords.longitude];
        placePin(here);
        map.setView(here, 15);
        setCoords(here[0], here[1], 'Pin set from your location.');
      }, (error) => {
        if (!statusEl) return;
        // Distinguish the three failure modes. A desktop with no location
        // provider fails with POSITION_UNAVAILABLE, which is not a permission
        // problem and cannot be fixed by changing browser settings.
        statusEl.textContent = ({
          1: 'Location permission denied. Allow it in your browser, or click the map to place the pin.',
          2: 'No location provider on this device. Click the map or drag the pin.',
          3: 'Location lookup timed out. Click the map or drag the pin.',
        })[error.code] || 'Location unavailable. Click the map or drag the pin.';
      });
    });
  } else if (locateButton) {
    locateButton.hidden = true;
  }
}

const meetingForm = document.querySelector('[data-meeting-form]');
if (meetingForm) {
  const meetingInput = meetingForm.querySelector('[name="meeting_at"]');
  if (meetingInput) {
    const error = document.createElement('p');
    error.className = 'field-error';
    error.setAttribute('role', 'alert');
    meetingInput.insertAdjacentElement('afterend', error);

    const pakistanParts = value => Object.fromEntries(new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Karachi', hourCycle: 'h12',
      day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit',
    }).formatToParts(value).filter(part => part.type !== 'literal').map(part => [part.type, part.value]));
    const setNextAvailableHour = () => {
      const next = new Date(Date.now() + 60 * 60 * 1000);
      next.setMinutes(0, 0, 0);
      const parts = pakistanParts(next);
      meetingInput.value = `${parts.day}-${parts.month}-${parts.year} ${parts.hour}:${parts.minute} ${parts.dayPeriod || 'AM'}`;
      meetingInput.dispatchEvent(new Event('input', {bubbles: true}));
    };
    const meetingNow = meetingForm.querySelector('[data-meeting-now]');
    if (meetingNow) meetingNow.addEventListener('click', setNextAvailableHour);
    if (!meetingInput.value) setNextAvailableHour();

    const setMeetingError = message => {
      meetingInput.setCustomValidity(message);
      meetingInput.classList.toggle('has-error', Boolean(message));
      error.textContent = message;
      error.hidden = !message;
    };

    const formatMeeting = () => {
      const raw = meetingInput.value.toUpperCase();
      const digits = raw.replace(/[^0-9]/g, '').slice(0, 10);
      const suffixMatch = raw.match(/(?:A|AM|P|PM)$/);
      const suffix = suffixMatch ? suffixMatch[0] : '';
      const parts = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 6), digits.slice(6, 8), digits.slice(8, 10)];
      let value = parts[0];
      if (digits.length > 2) value += '-' + parts[1];
      if (digits.length > 4) value += '-' + parts[2];
      if (digits.length > 6) value += ' ' + parts[3];
      if (digits.length > 8) value += ':' + parts[4];
      if (suffix && digits.length > 8) value += ' ' + suffix;
      meetingInput.value = value;

      if (!value) return setMeetingError('Enter a meeting date and time.');
      const match = value.match(/^(\d{1,2})-(\d{1,2})-(\d{2}) (\d{1,2}):(\d{2}) (AM|PM)$/);
      if (!match) return setMeetingError('Use DD-MM-YY hh:mm AM/PM.');
      const [, day, month, , hour, minute] = match;
      if (+day < 1 || +day > 31) return setMeetingError('Day must be between 1 and 31.');
      if (+month < 1 || +month > 12) return setMeetingError('Month must be between 1 and 12.');
      if (+hour < 1 || +hour > 12) return setMeetingError('Hour must be between 1 and 12.');
      if (+minute > 59) return setMeetingError('Minutes must be between 00 and 59.');
      setMeetingError('');
    };

    meetingInput.addEventListener('input', formatMeeting);
    meetingInput.addEventListener('blur', formatMeeting);
    meetingInput.addEventListener('focus', () => setMeetingError(''));
    meetingInput.form.addEventListener('submit', formatMeeting);
    if (meetingInput.value) formatMeeting();
    else error.hidden = true;
  }
}

document.querySelectorAll('[data-reject-match]').forEach(rejectForm => {
  rejectForm.addEventListener('submit', event => {
    if (!window.confirm('Dismiss this possible match? You can restore it later.')) {
      event.preventDefault();
    }
  });
});

document.querySelectorAll('[data-restore-match]').forEach(restoreForm => {
  restoreForm.addEventListener('submit', event => {
    if (!window.confirm('Restore and recheck this possible match?')) {
      event.preventDefault();
    }
  });
});

const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
const sidebarClose = document.querySelector('[data-sidebar-close]');
const sidebar = document.getElementById('app-sidebar');
const narrowLayout = window.matchMedia('(max-width:900px)');
const syncSidebar = () => {
  const isOpen = document.body.classList.contains('sidebar-open');
  if (sidebar) sidebar.inert = narrowLayout.matches && !isOpen;
  document.querySelectorAll('.workspace, .mobile-bar').forEach(element => {
    element.inert = narrowLayout.matches && isOpen;
  });
};
const closeSidebar = () => {
  document.body.classList.remove('sidebar-open');
  if (sidebarToggle) sidebarToggle.setAttribute('aria-expanded', 'false');
  syncSidebar();
};

if (sidebarToggle) {
  sidebarToggle.addEventListener('click', () => {
    const isOpen = document.body.classList.toggle('sidebar-open');
    sidebarToggle.setAttribute('aria-expanded', String(isOpen));
    syncSidebar();
    if (isOpen && sidebar) sidebar.querySelector('[data-sidebar-dismiss]').focus();
  });
}

if (sidebarClose) {
  sidebarClose.addEventListener('click', () => { closeSidebar(); sidebarToggle.focus(); });
}
document.querySelector('[data-sidebar-dismiss]')?.addEventListener('click', () => {
  closeSidebar();
  sidebarToggle.focus();
});
narrowLayout.addEventListener('change', closeSidebar);
syncSidebar();

document.querySelectorAll('.side-nav a').forEach(link => {
  link.addEventListener('click', closeSidebar);
});

document.addEventListener('keydown', event => {
  if (event.key === 'Tab' && document.body.classList.contains('sidebar-open') && sidebar) {
    const controls = [...sidebar.querySelectorAll('a[href], button, input')].filter(element => !element.disabled && element.getClientRects().length);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }
  if (event.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
    closeSidebar();
    if (sidebarToggle) sidebarToggle.focus();
  }
});

const reportsToggle = document.querySelector('[data-reports-toggle]');
const reportsBody = reportsToggle ? document.getElementById(reportsToggle.getAttribute('aria-controls')) : null;
if (reportsToggle && reportsBody) {
  reportsToggle.addEventListener('click', () => {
    const isOpen = reportsBody.classList.toggle('open');
    reportsToggle.setAttribute('aria-expanded', String(isOpen));
  });
}
