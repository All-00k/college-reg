// Registrations list: fetch, search, and export to CSV.
(function () {
  var all = [];
  var rowsEl = document.getElementById('rows');
  var emptyEl = document.getElementById('empty');
  var countEl = document.getElementById('count');
  var keybox = document.getElementById('keybox');
  var keyMsg = document.getElementById('keyMsg');
  var keyInput = document.getElementById('adminKey');

  function getKey() {
    try { return sessionStorage.getItem('adminKey') || ''; } catch (e) { return ''; }
  }

  function load() {
    var headers = {};
    if (getKey()) headers['X-Admin-Key'] = getKey();
    fetch('/api/registrations', { headers: headers })
      .then(function (res) {
        if (res.status === 401) {
          keybox.classList.add('show');
          keyMsg.textContent = getKey() ? 'That key was not accepted.' : 'Enter the admin key to view registrations.';
          all = [];
          render();
          return null;
        }
        return res.json();
      })
      .then(function (data) {
        if (!data) return;
        keybox.classList.remove('show');
        all = data.registrations || [];
        render();
      })
      .catch(function () {
        emptyEl.textContent = 'Could not load registrations.';
        emptyEl.hidden = false;
      });
  }

  function matches(r, q) {
    if (!q) return true;
    q = q.toLowerCase();
    return [r.id, r.full_name, r.enrollment, r.email, r.college, r.city, r.course, r.branch]
      .join(' ').toLowerCase().indexOf(q) > -1;
  }

  function cell(text, mono) {
    var td = document.createElement('td');
    td.textContent = text;
    if (mono) td.className = 'mono';
    return td;
  }

  function visible() {
    var q = document.getElementById('q').value.trim();
    return all.filter(function (r) { return matches(r, q); });
  }

  function render() {
    var list = visible();
    rowsEl.innerHTML = '';
    list.forEach(function (r) {
      var tr = document.createElement('tr');
      tr.appendChild(cell(r.id, true));
      tr.appendChild(cell(r.full_name));
      tr.appendChild(cell(r.enrollment, true));
      tr.appendChild(cell(r.college));
      tr.appendChild(cell(r.course + ' · ' + r.branch));
      tr.appendChild(cell(r.year));
      tr.appendChild(cell(r.email));
      tr.appendChild(cell('+91 ' + r.phone));
      tr.appendChild(cell(r.city));
      tr.appendChild(cell(r.created_at.replace('T', ' ').slice(0, 16) + ' UTC'));
      rowsEl.appendChild(tr);
    });
    emptyEl.textContent = 'No registrations to show.';
    emptyEl.hidden = list.length > 0;
    countEl.textContent = list.length + ' of ' + all.length + ' shown';
  }

  function csvCell(v) {
    v = String(v == null ? '' : v);
    // Stop spreadsheet apps from running cells that start with a formula character.
    if (/^[=+\-@]/.test(v)) v = "'" + v;
    return '"' + v.replace(/"/g, '""') + '"';
  }

  function downloadCsv() {
    var cols = ['id', 'created_at', 'full_name', 'dob', 'gender', 'enrollment', 'college', 'course',
                'branch', 'year', 'stay', 'email', 'phone', 'city', 'interests', 'notes'];
    var lines = [cols.join(',')];
    visible().forEach(function (r) {
      lines.push(cols.map(function (c) {
        return csvCell(Array.isArray(r[c]) ? r[c].join('; ') : r[c]);
      }).join(','));
    });
    var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'registrations.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  document.getElementById('q').addEventListener('input', render);
  document.getElementById('csvBtn').addEventListener('click', downloadCsv);
  document.getElementById('keyBtn').addEventListener('click', function () {
    try { sessionStorage.setItem('adminKey', keyInput.value); } catch (e) {}
    load();
  });
  keyInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') document.getElementById('keyBtn').click();
  });

  load();
})();
