// ===== Collections Tab - Add to index.html <script> block =====
// TABS entry: { id: 'collections', label: 'Collections', load: loadCollections }

function loadCollections() {
  setActive('collections');
  setStatus('Loading...');
  fetch('/cgi-bin/collections.cgi')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderCollections(data);
      setStatus('');
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function renderCollections(data) {
  var content = document.getElementById('content');
  var html = '<div style="margin-bottom:12px;">' +
    '<button class="btn" onclick="showCreateCollection()">Create Collection</button>' +
    '</div>';

  if (!data.collections || data.collections.length === 0) {
    html += '<div class="empty-state">No collections yet. Tap <b>Create Collection</b> to get started.</div>';
    content.innerHTML = html;
    return;
  }

  for (var i = 0; i < data.collections.length; i++) {
    var coll = data.collections[i];
    var safeId = escapeHtml(coll.id);
    var safeName = escapeHtml(coll.name);
    var bookCount = coll.books ? coll.books.length : 0;

    html += '<div class="card">' +
      '<div class="card-header">' +
      '<div><span class="card-title">' + safeName + '</span> ' +
      '<span class="card-subtitle">' + bookCount + ' books</span></div>' +
      '<div style="display:flex;gap:8px;">' +
      '<button class="btn btn-toggle" onclick="toggleCard(this)">Show</button>' +
      '<button class="btn" onclick="addToCollection(\'' + safeId.replace(/'/g, "\\'") + '\')">Add Books</button>' +
      '<button class="btn btn-danger" onclick="deleteCollection(\'' + safeId.replace(/'/g, "\\'") + '\')">Delete</button>' +
      '</div></div>' +
      '<div class="card-body" style="display:none;"><div class="card-body-inner">';

    if (bookCount === 0) {
      html += '<div class="empty-state">No books in this collection.</div>';
    } else {
      html += '<div class="series-books">';
      for (var j = 0; j < coll.books.length; j++) {
        var book = coll.books[j];
        var safeTitle = escapeHtml(book.title);
        var safeAuthor = escapeHtml(book.author || '');
        var safeBookKey = escapeHtml(book.key);
        html += '<div class="book-item" style="display:flex;justify-content:space-between;align-items:center;">' +
          '<span>' + safeTitle + (safeAuthor ? ' <span style="color:var(--fg-muted);font-size:12px;">' + safeAuthor + '</span>' : '') + '</span>' +
          '<button class="btn btn-danger" style="padding:2px 8px;font-size:11px;" onclick="removeFromCollection(\'' + safeId.replace(/'/g, "\\'") + '\',\'' + safeBookKey.replace(/'/g, "\\'") + '\')">Remove</button>' +
          '</div>';
      }
      html += '</div>';
    }

    html += '</div></div></div>';
  }

  content.innerHTML = html;
}

function showCreateCollection() {
  setActive('collections');
  setStatus('Loading books...');
  fetch('/cgi-bin/collection_books.cgi')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderCreateCollectionForm(data.books || []);
      setStatus('');
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function renderCreateCollectionForm(books) {
  var content = document.getElementById('content');
  var html = '<div>' +
    '<div class="panel-header">Collection Details</div>' +
    '<input type="text" id="collName" class="input-field" placeholder="Collection name">' +
    '<div class="panel-header" style="margin-top:12px;">Select Books</div>' +
    '<input type="text" id="collBookFilter" class="input-field input-small" placeholder="Filter by title or author..." oninput="filterCollBooks()">' +
    '<div id="collBookList" style="max-height:400px;overflow-y:auto;">';

  for (var i = 0; i < books.length; i++) {
    var b = books[i];
    var safeKey = escapeHtml(b.key);
    var safeTitle = escapeHtml(b.title);
    var safeAuthor = escapeHtml(b.author || '');
    html += '<label class="coll-book-option" data-title="' + safeTitle.toLowerCase() + '" data-author="' + safeAuthor.toLowerCase() + '" style="display:flex;align-items:center;gap:8px;padding:6px 4px;cursor:pointer;user-select:none;">' +
      '<input type="checkbox" value="' + safeKey + '">' +
      '<span>' + safeTitle + (safeAuthor ? ' <span style="color:var(--fg-muted);font-size:12px;">' + safeAuthor + '</span>' : '') + '</span>' +
      '</label>';
  }

  html += '</div>' +
    '<button class="btn" onclick="saveCollection()" style="width:100%;padding:12px;font-size:15px;margin-top:12px;">Create Collection</button>' +
    '<button class="btn" onclick="loadCollections()" style="width:100%;padding:8px;margin-top:8px;">Cancel</button>' +
    '</div>';

  content.innerHTML = html;
}

function filterCollBooks() {
  var filter = (document.getElementById('collBookFilter').value || '').toLowerCase();
  var items = document.querySelectorAll('.coll-book-option');
  for (var i = 0; i < items.length; i++) {
    var title = items[i].getAttribute('data-title') || '';
    var author = items[i].getAttribute('data-author') || '';
    items[i].style.display = (title.indexOf(filter) >= 0 || author.indexOf(filter) >= 0) ? '' : 'none';
  }
}

function saveCollection() {
  var name = (document.getElementById('collName').value || '').trim();
  if (!name) { setStatus('Enter a collection name.'); return; }

  var checks = document.querySelectorAll('#collBookList input[type="checkbox"]:checked');
  if (checks.length === 0) { setStatus('Select at least one book.'); return; }

  var keys = [];
  for (var i = 0; i < checks.length; i++) keys.push(checks[i].value);

  setStatus('Creating collection...');
  var body = 'name=' + encodeURIComponent(name) + '&books=' + encodeURIComponent(keys.join(','));

  fetch('/cgi-bin/collection_create.cgi', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: body
  })
    .then(function(r) { return r.text(); })
    .then(function(text) {
      setStatus(text);
      loadCollections();
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function addToCollection(collId) {
  setActive('collections');
  setStatus('Loading books...');
  fetch('/cgi-bin/collection_books.cgi')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      renderAddToCollectionForm(collId, data.books || []);
      setStatus('');
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function renderAddToCollectionForm(collId, books) {
  var content = document.getElementById('content');
  var safeId = escapeHtml(collId);
  var html = '<div>' +
    '<div class="panel-header">Add Books to Collection</div>' +
    '<input type="text" id="collBookFilter" class="input-field input-small" placeholder="Filter by title or author..." oninput="filterCollBooks()">' +
    '<div id="collBookList" style="max-height:400px;overflow-y:auto;">';

  for (var i = 0; i < books.length; i++) {
    var b = books[i];
    var safeKey = escapeHtml(b.key);
    var safeTitle = escapeHtml(b.title);
    var safeAuthor = escapeHtml(b.author || '');
    html += '<label class="coll-book-option" data-title="' + safeTitle.toLowerCase() + '" data-author="' + safeAuthor.toLowerCase() + '" style="display:flex;align-items:center;gap:8px;padding:6px 4px;cursor:pointer;user-select:none;">' +
      '<input type="checkbox" value="' + safeKey + '">' +
      '<span>' + safeTitle + (safeAuthor ? ' <span style="color:var(--fg-muted);font-size:12px;">' + safeAuthor + '</span>' : '') + '</span>' +
      '</label>';
  }

  html += '</div>' +
    '<input type="hidden" id="addCollId" value="' + safeId + '">' +
    '<button class="btn" onclick="saveAddToCollection()" style="width:100%;padding:12px;font-size:15px;margin-top:12px;">Add Selected Books</button>' +
    '<button class="btn" onclick="loadCollections()" style="width:100%;padding:8px;margin-top:8px;">Cancel</button>' +
    '</div>';

  content.innerHTML = html;
}

function saveAddToCollection() {
  var collId = document.getElementById('addCollId').value;
  var checks = document.querySelectorAll('#collBookList input[type="checkbox"]:checked');
  if (checks.length === 0) { setStatus('Select at least one book.'); return; }

  var keys = [];
  for (var i = 0; i < checks.length; i++) keys.push(checks[i].value);

  // Extract collection name from URN for the create endpoint
  var collKey = collId.replace('urn:collection:1:', '');
  setStatus('Adding books...');
  var body = 'name=' + encodeURIComponent(collKey) + '&books=' + encodeURIComponent(keys.join(','));

  fetch('/cgi-bin/collection_create.cgi', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: body
  })
    .then(function(r) { return r.text(); })
    .then(function(text) {
      setStatus(text);
      loadCollections();
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function removeFromCollection(collId, bookKey) {
  setStatus('Removing book...');
  fetch('/cgi-bin/collection_remove.cgi', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(collId) + '&book=' + encodeURIComponent(bookKey)
  })
    .then(function(r) { return r.text(); })
    .then(function(text) {
      setStatus(text);
      loadCollections();
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}

function deleteCollection(collId) {
  if (!confirm('Delete this collection? Books will remain in your library.')) return;
  setStatus('Deleting collection...');
  fetch('/cgi-bin/collection_remove.cgi', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(collId)
  })
    .then(function(r) { return r.text(); })
    .then(function(text) {
      setStatus(text);
      loadCollections();
    })
    .catch(function(e) { setStatus('Error: ' + e); });
}
