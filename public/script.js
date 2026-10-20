// Registration form: validate in the browser, then POST to /api/register.
(function () {
  var form = document.getElementById('reg');
  var done = document.getElementById('done');
  var intro = document.querySelector('.intro');
  var statusEl = document.getElementById('status');
  var submitBtn = document.getElementById('submitBtn');
  var required = ['fullName', 'dob', 'enrollment', 'college', 'course', 'branch', 'year', 'email', 'phone', 'city', 'consent'];
  var touched = {};

  function val(name) {
    var el = form.elements[name];
    if (name === 'consent') return el.checked;
    return (el.value || '').trim();
  }

  var rules = {
    fullName: function (v) {
      if (v.length < 2) return 'Enter your full name as it appears on your college ID.';
      if (!/^[\p{L}\p{M} .'\-]+$/u.test(v)) return 'Use letters only, with no numbers or symbols.';
      return '';
    },
    dob: function (v) {
      if (!v) return 'Select your date of birth.';
      var d = new Date(v), now = new Date();
      if (isNaN(d)) return 'Enter a valid date of birth.';
      var age = now.getFullYear() - d.getFullYear();
      var m = now.getMonth() - d.getMonth();
      if (m < 0 || (m === 0 && now.getDate() < d.getDate())) age--;
      return age < 16 || age > 45 ? 'Enter a valid date of birth. Students must be 16 or older.' : '';
    },
    enrollment: function (v) {
      return /^[A-Za-z0-9\/\-]{5,20}$/.test(v) ? '' : 'Enter 5 to 20 letters or digits, as printed on your ID card.';
    },
    college: function (v) { return v.length >= 3 ? '' : 'Enter your college or university name.'; },
    course: function (v) { return v ? '' : 'Choose your course.'; },
    branch: function (v) { return v.length >= 2 ? '' : 'Enter your branch or department.'; },
    year: function (v) { return v ? '' : 'Select your year of study.'; },
    email: function (v) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v) ? '' : 'Enter a valid email address, like you@college.edu.in.';
    },
    phone: function (v) {
      return /^[6-9]\d{9}$/.test(v.replace(/\s+/g, '')) ? '' : 'Enter a 10-digit Indian mobile number starting with 6, 7, 8 or 9.';
    },
    city: function (v) { return v.length >= 2 ? '' : 'Enter your city.'; },
    consent: function (v) { return v ? '' : 'Tick this box to confirm and continue.'; }
  };

  function wrapper(name) { return form.querySelector('[data-field="' + name + '"]'); }

  function setError(name, msg) {
    var w = wrapper(name);
    if (!w) return false;
    w.classList.toggle('invalid', !!msg);
    w.querySelector('.err').textContent = msg;
    return true;
  }

  function show(name) {
    var msg = rules[name](val(name));
    setError(name, msg);
    return msg;
  }

  function progress() {
    var ok = required.filter(function (n) { return !rules[n](val(n)); }).length;
    document.getElementById('pcount').textContent = ok + ' / ' + required.length;
    document.getElementById('pbar').style.width = Math.round(ok / required.length * 100) + '%';
  }

  function fieldName(target) {
    return target && target.name && required.indexOf(target.name) > -1 ? target.name : null;
  }

  form.addEventListener('input', function (e) {
    var n = fieldName(e.target);
    if (n === 'phone') {
      var d = e.target.value.replace(/\D/g, '').slice(0, 10);
      e.target.value = d.length > 5 ? d.slice(0, 5) + ' ' + d.slice(5) : d;
    }
    if (n === 'enrollment') e.target.value = e.target.value.toUpperCase();
    if (n && (touched[n] || wrapper(n).classList.contains('invalid'))) show(n);
    progress();
  });

  form.addEventListener('change', function (e) {
    var n = fieldName(e.target);
    if (n && (e.target.type === 'radio' || e.target.type === 'checkbox' || e.target.tagName === 'SELECT')) {
      touched[n] = true;
      show(n);
    }
    progress();
  });

  form.addEventListener('focusout', function (e) {
    var n = fieldName(e.target);
    if (n && e.target.value !== '' && e.target.type !== 'radio' && e.target.type !== 'checkbox') {
      touched[n] = true;
      show(n);
    }
  });

  // Students must be at least 16: stop the date picker above that limit.
  var max = new Date();
  max.setFullYear(max.getFullYear() - 16);
  document.getElementById('dob').max = max.toISOString().slice(0, 10);

  function payload() {
    var interests = Array.prototype.map.call(
      form.querySelectorAll('input[name="interests"]:checked'),
      function (c) { return c.value; });
    return {
      fullName: val('fullName'), dob: val('dob'), gender: val('gender'),
      enrollment: val('enrollment'), college: val('college'), course: val('course'),
      branch: val('branch'), year: val('year'), stay: val('stay'),
      email: val('email'), phone: val('phone'), city: val('city'),
      interests: interests, notes: val('notes'), consent: val('consent')
    };
  }

  function focusField(name) {
    var w = wrapper(name);
    if (!w) return;
    w.scrollIntoView({ block: 'center', behavior: 'smooth' });
    var f = w.querySelector('input, select');
    if (f) f.focus({ preventScroll: true });
  }

  function showDone(data, p) {
    document.getElementById('regId').textContent = data.id;
    document.getElementById('doneTitle').textContent = p.fullName.split(/\s+/)[0] + ', you are registered';
    var rows = [
      ['Name', p.fullName],
      ['Enrollment', p.enrollment.toUpperCase()],
      ['College', p.college],
      ['Course', p.course + ', ' + p.branch + ' (' + p.year + ')'],
      ['Email', p.email],
      ['Mobile', '+91 ' + p.phone],
      ['City', p.city]
    ];
    if (p.interests.length) rows.push(['Interests', p.interests.join(', ')]);
    var dl = document.getElementById('summary');
    dl.innerHTML = '';
    rows.forEach(function (r) {
      var dt = document.createElement('dt'); dt.textContent = r[0];
      var dd = document.createElement('dd'); dd.textContent = r[1];
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    form.hidden = true;
    intro.hidden = true;
    done.hidden = false;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var bad = [];
    required.forEach(function (n) {
      touched[n] = true;
      if (show(n)) bad.push(n);
    });
    progress();
    if (bad.length) {
      statusEl.textContent = bad.length === 1 ? 'One field needs your attention.' : bad.length + ' fields need your attention.';
      focusField(bad[0]);
      return;
    }
    statusEl.textContent = '';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Submitting…';
    var p = payload();

    fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(p)
    }).then(function (res) {
      return res.json().catch(function () { return {}; }).then(function (data) {
        return { status: res.status, data: data };
      });
    }).then(function (r) {
      if (r.status === 201) return showDone(r.data, p);
      var errors = r.data.errors || {};
      var first = null;
      Object.keys(errors).forEach(function (k) {
        if (setError(k, errors[k]) && !first) first = k;
      });
      statusEl.textContent = first ? 'Please fix the highlighted fields.' : (r.data.error || 'Something went wrong. Please try again.');
      if (first) focusField(first);
    }).catch(function () {
      statusEl.textContent = 'Could not reach the server. Check your connection and try again.';
    }).then(function () {
      submitBtn.disabled = false;
      submitBtn.textContent = 'Submit registration';
    });
  });

  document.getElementById('copyBtn').addEventListener('click', function () {
    var btn = this, text = document.getElementById('regId').textContent;
    function flash(msg) {
      btn.textContent = msg;
      setTimeout(function () { btn.textContent = 'Copy ID'; }, 1600);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { flash('Copied'); }, function () { flash('Select and copy'); });
    } else {
      flash('Select and copy');
    }
  });

  document.getElementById('againBtn').addEventListener('click', function () {
    form.reset();
    touched = {};
    required.forEach(function (n) { setError(n, ''); });
    done.hidden = true;
    form.hidden = false;
    intro.hidden = false;
    progress();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  progress();
})();
