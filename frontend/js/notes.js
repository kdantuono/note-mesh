// Notes management module for NoteMesh
class NotesManager {
    constructor() {
        this.currentNotes = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.currentFilters = {};
        this.currentNote = null;
        this.isEditing = false;
        this.shareList = []; // Lista degli utenti con cui condividere
    }

    // Load and display notes
    async loadNotes(page = 1, filters = {}) {
        try {
            this.currentPage = page;
            this.currentFilters = filters;

            // Combine different note sources based on filter
            const ownerFilter = filters.owner_filter || 'all';
            let notesData = { items: [], total: 0, pages: 1 };

            if (ownerFilter === 'all' || ownerFilter === 'owned') {
                const ownedNotes = await apiClient.getNotes(page, CONFIG.ITEMS_PER_PAGE, filters);
                notesData.items = [...notesData.items, ...this.markNotesAsType(ownedNotes.items, NOTE_TYPES.OWNED)];
                notesData.total += ownedNotes.total;
            }

            if (ownerFilter === 'all' || ownerFilter === 'shared_with_me') {
                try {
                    const sharedWithMe = await apiClient.getSharedWithMe(page, CONFIG.ITEMS_PER_PAGE);
                    if (sharedWithMe && sharedWithMe.shares && Array.isArray(sharedWithMe.shares)) {
                        // Backend returns 'shares' array, not 'items'
                        notesData.items = [...notesData.items, ...this.markNotesAsType(sharedWithMe.shares, NOTE_TYPES.SHARED_WITH_ME)];
                        notesData.total += sharedWithMe.total_count || 0;
                    }
                } catch (error) {
                    console.warn('Failed to load shared notes (this is normal for new users):', error.message);
                    // Continue without shared notes - this is normal for new users
                }
            }

            if (ownerFilter === 'all' || ownerFilter === 'shared_by_me') {
                try {
                    const sharedByMe = await apiClient.getMyShares(page, CONFIG.ITEMS_PER_PAGE);
                    if (sharedByMe && sharedByMe.shares && Array.isArray(sharedByMe.shares)) {
                        // Backend returns 'shares' array, not 'items'
                        notesData.items = [...notesData.items, ...this.markNotesAsType(sharedByMe.shares, NOTE_TYPES.SHARED_BY_ME)];
                        notesData.total += sharedByMe.total_count || 0;
                    }
                } catch (error) {
                    console.warn('Failed to load shared by me notes (this is normal for new users):', error.message);
                    // Continue without shared notes - this is normal for new users
                }
            }

            this.currentNotes = notesData.items;
            this.totalPages = Math.ceil(notesData.total / CONFIG.ITEMS_PER_PAGE);

            this.renderNotes();
            this.renderPagination();

        } catch (error) {
            console.error('Failed to load notes:', error);
            showToast(error.message || 'Failed to load notes', TOAST_TYPES.ERROR);
        }
    }

    // Mark notes with their type for visual distinction
    markNotesAsType(notes, type) {
        return notes.map(note => ({
            ...note,
            note_type: type
        }));
    }

    // Render notes grid
    renderNotes() {
        const notesGrid = document.getElementById('notesGrid');

        if (this.currentNotes.length === 0) {
            notesGrid.innerHTML = `
                <div class="no-notes">
                    <i class="fas fa-sticky-note" style="font-size: 3rem; color: #ccc; margin-bottom: 1rem;"></i>
                    <p>No notes found. <a href="#" id="createFirstNote">Create your first note</a></p>
                </div>
            `;

            // Set up create first note link
            document.getElementById('createFirstNote')?.addEventListener('click', (e) => {
                e.preventDefault();
                this.showNoteEditor();
            });

            return;
        }

        const notesHTML = this.currentNotes.map(note => this.createNoteCard(note)).join('');
        notesGrid.innerHTML = notesHTML;

        // Set up note card click handlers
        notesGrid.querySelectorAll('.note-card').forEach(card => {
            card.addEventListener('click', () => {
                const noteId = card.dataset.noteId;
                this.showNoteDetail(noteId);
            });
        });
    }

    // Create HTML for a single note card
    createNoteCard(note) {
        const preview = this.createContentPreview(note.content);
        const tags = note.tags ? note.tags.slice(0, 3) : [];
        const remainingTags = note.tags ? Math.max(0, note.tags.length - 3) : 0;

        const typeClass = note.note_type || NOTE_TYPES.OWNED;
        const typeLabel = this.getTypeLabel(typeClass);

        return `
            <div class="note-card ${typeClass}" data-note-id="${note.id}">
                <div class="note-card-header">
                    <div>
                        <h3 class="note-title">${this.escapeHtml(note.title)}</h3>
                        <div class="note-type ${typeClass}">${typeLabel}</div>
                    </div>
                </div>
                <div class="note-preview">${this.escapeHtml(preview)}</div>
                <div class="note-meta">
                    <span><i class="fas fa-user"></i> ${this.escapeHtml(note.owner?.full_name || note.owner?.username || 'Unknown')}</span>
                    <span><i class="fas fa-calendar"></i> ${this.formatDate(note.created_at)}</span>
                </div>
                <div class="note-tags">
                    ${tags.map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`).join('')}
                    ${remainingTags > 0 ? `<span class="tag">+${remainingTags} more</span>` : ''}
                </div>
            </div>
        `;
    }

    // Get type label for display
    getTypeLabel(type) {
        switch (type) {
            case NOTE_TYPES.OWNED:
                return 'My Note';
            case NOTE_TYPES.SHARED_WITH_ME:
                return 'Shared';
            case NOTE_TYPES.SHARED_BY_ME:
                return 'Shared by Me';
            default:
                return 'Note';
        }
    }

    // Create content preview
    createContentPreview(content) {
        if (!content) return '';
        return content.length > CONFIG.MAX_CONTENT_PREVIEW
            ? content.substring(0, CONFIG.MAX_CONTENT_PREVIEW) + '...'
            : content;
    }

    // Render pagination
    renderPagination() {
        const pagination = document.getElementById('pagination');

        if (this.totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let paginationHTML = `
            <button ${this.currentPage === 1 ? 'disabled' : ''} data-page="${this.currentPage - 1}">
                <i class="fas fa-chevron-left"></i>
            </button>
        `;

        // Page numbers
        const startPage = Math.max(1, this.currentPage - 2);
        const endPage = Math.min(this.totalPages, this.currentPage + 2);

        if (startPage > 1) {
            paginationHTML += `<button data-page="1">1</button>`;
            if (startPage > 2) paginationHTML += `<span>...</span>`;
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button ${i === this.currentPage ? 'class="active"' : ''} data-page="${i}">${i}</button>
            `;
        }

        if (endPage < this.totalPages) {
            if (endPage < this.totalPages - 1) paginationHTML += `<span>...</span>`;
            paginationHTML += `<button data-page="${this.totalPages}">${this.totalPages}</button>`;
        }

        paginationHTML += `
            <button ${this.currentPage === this.totalPages ? 'disabled' : ''} data-page="${this.currentPage + 1}">
                <i class="fas fa-chevron-right"></i>
            </button>
        `;

        pagination.innerHTML = paginationHTML;

        // Set up pagination click handlers
        pagination.querySelectorAll('button[data-page]').forEach(button => {
            button.addEventListener('click', () => {
                const page = parseInt(button.dataset.page);
                this.loadNotes(page, this.currentFilters);
            });
        });
    }

    // Show note detail view
    async showNoteDetail(noteId) {
        try {
            const note = await apiClient.getNote(noteId);
            this.currentNote = note;

            document.getElementById('dashboardSection').classList.add('hidden');
            document.getElementById('noteDetailSection').classList.remove('hidden');
            document.getElementById('noteEditorSection').classList.add('hidden');

            this.renderNoteDetail(note);

        } catch (error) {
            console.error('Failed to load note:', error);
            showToast(error.message || 'Failed to load note', TOAST_TYPES.ERROR);
        }
    }

    // Render note detail view
    renderNoteDetail(note) {
        document.getElementById('noteTitle').textContent = note.title;
        document.getElementById('noteContent').textContent = note.content;

        // Note meta information
        const ownerName = note.owner?.full_name || note.owner?.username || 'Unknown';
        const createdDate = this.formatDate(note.created_at);
        const viewCount = note.view_count || 0;

        document.getElementById('noteOwner').innerHTML = `<i class="fas fa-user"></i> ${this.escapeHtml(ownerName)}`;
        document.getElementById('noteDate').innerHTML = `<i class="fas fa-calendar"></i> ${createdDate}`;
        document.getElementById('noteViews').innerHTML = `<i class="fas fa-eye"></i> ${viewCount} views`;

        // Tags
        const tagsContainer = document.getElementById('noteTags');
        if (note.tags && note.tags.length > 0) {
            tagsContainer.innerHTML = note.tags
                .map(tag => `<span class="tag">${this.escapeHtml(tag)}</span>`)
                .join('');
        } else {
            tagsContainer.innerHTML = '<span class="text-muted">No tags</span>';
        }

        // Hyperlinks
        const hyperlinksContainer = document.getElementById('noteHyperlinks');
        if (note.hyperlinks && note.hyperlinks.length > 0) {
            hyperlinksContainer.innerHTML = `
                <h4>Links:</h4>
                ${note.hyperlinks
                    .map(link => `<a href="${link}" target="_blank" rel="noopener">${link}</a>`)
                    .join('')}
            `;
            hyperlinksContainer.style.display = 'block';
        } else {
            hyperlinksContainer.style.display = 'none';
        }

        // Show/hide action buttons based on ownership
        const currentUser = authManager.getCurrentUser();
        const isOwner = note.owner && note.owner.id === currentUser?.id;

        document.getElementById('editNoteBtn').style.display = isOwner ? 'inline-flex' : 'none';
        document.getElementById('shareNoteBtn').style.display = isOwner ? 'inline-flex' : 'none';
        document.getElementById('deleteNoteBtn').style.display = isOwner ? 'inline-flex' : 'none';
    }

    // Show note editor
    showNoteEditor(noteId = null) {
        this.isEditing = !!noteId;

        document.getElementById('dashboardSection').classList.add('hidden');
        document.getElementById('noteDetailSection').classList.add('hidden');
        document.getElementById('noteEditorSection').classList.remove('hidden');

        document.getElementById('editorTitle').textContent = this.isEditing ? 'Edit Note' : 'Create New Note';

        if (this.isEditing && this.currentNote) {
            this.populateNoteForm(this.currentNote);
        } else {
            document.getElementById('noteForm').reset();
            // Reset share list for new notes
            this.shareList = [];
            this.renderShareList();
            // Hide existing shares section for new notes
            document.getElementById('existingShares').style.display = 'none';
        }
    }

    // Populate note form with existing data
    populateNoteForm(note) {
        document.getElementById('noteTitleInput').value = note.title || '';
        document.getElementById('noteContentInput').value = note.content || '';
        document.getElementById('noteTagsInput').value = note.tags ? note.tags.join(', ') : '';
        document.getElementById('isPinnedInput').checked = note.is_pinned || false;

        // Reset share list when editing
        this.shareList = [];
        this.renderShareList();

        // Load existing shares for this note
        this.loadExistingShares(note.id);
    }

    // Add user to share list
    addUserToShareList(username, permission = 'read') {
        // Check if user already exists
        const existingIndex = this.shareList.findIndex(user => user.username === username);
        if (existingIndex !== -1) {
            this.shareList[existingIndex].permission = permission;
        } else {
            this.shareList.push({ username, permission });
        }
        this.renderShareList();
    }

    // Remove user from share list
    removeUserFromShareList(username) {
        this.shareList = this.shareList.filter(user => user.username !== username);
        this.renderShareList();
    }

    // Render share list
    renderShareList() {
        const listElement = document.getElementById('sharedUsersList');
        if (this.shareList.length === 0) {
            listElement.innerHTML = '';
            return;
        }

        const html = this.shareList.map(user => `
            <div class="shared-user-tag">
                <span>${user.username}</span>
                <span class="permission">${user.permission}</span>
                <button type="button" class="remove-user" onclick="notesManager.removeUserFromShareList('${user.username}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');
        listElement.innerHTML = html;
    }

    // Share note with multiple users
    async shareNoteWithUsers(noteId, usersList) {
        const promises = usersList.map(user =>
            apiClient.shareNote(noteId, user.username, user.permission)
        );

        try {
            await Promise.all(promises);
            showToast(`Note shared with ${usersList.length} user(s)`, TOAST_TYPES.SUCCESS);
        } catch (error) {
            console.error('Failed to share with some users:', error);
            showToast('Note saved, but sharing failed for some users', TOAST_TYPES.WARNING);
        }
    }

    // Load existing shares for a note
    async loadExistingShares(noteId) {
        try {
            // Try to get shares using the API
            const sharesData = await apiClient.getShares('given', 1, 100);

            // Filter shares for this specific note
            const noteShares = sharesData.shares?.filter(share =>
                share.note_id === noteId || share.note?.id === noteId
            ) || [];

            this.renderExistingShares(noteShares);

            // Show existing shares section if there are any
            const existingSharesSection = document.getElementById('existingShares');
            if (noteShares.length > 0) {
                existingSharesSection.style.display = 'block';
            } else {
                existingSharesSection.style.display = 'none';
            }
        } catch (error) {
            console.error('Failed to load existing shares:', error);
            // Hide existing shares section on error
            document.getElementById('existingShares').style.display = 'none';
        }
    }

    // Render existing shares
    renderExistingShares(shares) {
        const listElement = document.getElementById('existingSharesList');

        if (shares.length === 0) {
            listElement.innerHTML = '<p style="color: #666; font-style: italic;">Not shared with anyone</p>';
            return;
        }

        const html = shares.map(share => `
            <div class="existing-share-tag" data-share-id="${share.id}">
                <span>${share.shared_with_username}</span>
                <span class="permission">${share.permission}</span>
                <button type="button" class="revoke-share" onclick="notesManager.revokeExistingShare('${share.id}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `).join('');

        listElement.innerHTML = html;
    }

    // Revoke existing share
    async revokeExistingShare(shareId) {
        try {
            await apiClient.revokeShare(shareId);
            showToast('Share revoked successfully', TOAST_TYPES.SUCCESS);

            // Reload existing shares to refresh the display
            if (this.currentNote?.id) {
                this.loadExistingShares(this.currentNote.id);
            }
        } catch (error) {
            console.error('Failed to revoke share:', error);
            showToast('Failed to revoke share', TOAST_TYPES.ERROR);
        }
    }

    // Handle note form submission
    async handleNoteSubmit(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const noteData = {
            title: formData.get('title').trim(),
            content: formData.get('content').trim(),
            is_pinned: formData.has('is_pinned')
        };

        // Parse tags
        const tagsInput = formData.get('tags').trim();
        if (tagsInput) {
            noteData.tags = tagsInput.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
        }

        if (!noteData.title || !noteData.content) {
            showToast('Please fill in title and content', TOAST_TYPES.ERROR);
            return;
        }

        try {
            let savedNote;
            if (this.isEditing && this.currentNote) {
                savedNote = await apiClient.updateNote(this.currentNote.id, noteData);
                showToast('Note updated successfully', TOAST_TYPES.SUCCESS);
            } else {
                savedNote = await apiClient.createNote(noteData);
                showToast('Note created successfully', TOAST_TYPES.SUCCESS);
            }

            // Handle sharing if users were selected
            if (this.shareList.length > 0 && savedNote?.id) {
                await this.shareNoteWithUsers(savedNote.id, this.shareList);
            }

            this.showDashboard();
            this.loadNotes(1, this.currentFilters);

        } catch (error) {
            console.error('Failed to save note:', error);
            showToast(error.message || 'Failed to save note', TOAST_TYPES.ERROR);
        }
    }

    // Handle note deletion
    async handleNoteDelete() {
        if (!this.currentNote) return;

        if (!confirm('Are you sure you want to delete this note? This action cannot be undone.')) {
            return;
        }

        try {
            await apiClient.deleteNote(this.currentNote.id);
            showToast('Note deleted successfully', TOAST_TYPES.SUCCESS);
            this.showDashboard();
            this.loadNotes(1, this.currentFilters);

        } catch (error) {
            console.error('Failed to delete note:', error);
            showToast(error.message || 'Failed to delete note', TOAST_TYPES.ERROR);
        }
    }

    // Handle search
    async handleSearch() {
        const searchQuery = document.getElementById('searchInput').value.trim();
        const tagFilter = document.getElementById('tagFilter').value.trim();
        const ownerFilter = document.getElementById('ownerFilter').value;

        // If no search query, load regular notes
        if (!searchQuery && !tagFilter) {
            const filters = {};
            if (ownerFilter !== 'all') {
                filters.owner_filter = ownerFilter;
            }
            this.loadNotes(1, filters);
            return;
        }

        try {
            // Use search API for text search
            const filters = {
                page: 1,
                per_page: CONFIG.ITEMS_PER_PAGE
            };

            // Add tag filters
            if (tagFilter) {
                filters.tags = [tagFilter];
            }

            const searchResults = await apiClient.searchNotes(searchQuery || '*', filters);

            // Process search results to match loadNotes format
            this.currentNotes = this.markNotesAsType(searchResults.items || [], NOTE_TYPES.OWNED);
            this.currentPage = searchResults.page || 1;
            this.totalPages = searchResults.pages || 1;
            this.currentFilters = { q: searchQuery, tagFilter, ownerFilter };

            this.renderNotes();
            this.renderPagination();

            // Show search info
            const searchInfo = searchQuery ?
                `Found ${searchResults.total || 0} results for "${searchQuery}"` :
                `Filtered by tag: ${tagFilter}`;

            showToast(searchInfo, TOAST_TYPES.INFO);

        } catch (error) {
            console.error('Search failed:', error);
            showToast(error.message || 'Search failed', TOAST_TYPES.ERROR);
        }
    }

    // Clear all filters
    clearFilters() {
        document.getElementById('searchInput').value = '';
        document.getElementById('tagFilter').value = '';
        document.getElementById('ownerFilter').value = 'all';

        this.loadNotes(1, {});
    }

    // Show dashboard
    showDashboard() {
        document.getElementById('authSection').classList.add('hidden');
        document.getElementById('dashboardSection').classList.remove('hidden');
        document.getElementById('noteDetailSection').classList.add('hidden');
        document.getElementById('noteEditorSection').classList.add('hidden');
    }

    // Utility methods
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    // Initialize notes management
    initializeNotes() {
        // Set up search
        document.getElementById('searchBtn').addEventListener('click', () => this.handleSearch());
        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleSearch();
        });

        // Set up filters
        document.getElementById('tagFilter').addEventListener('change', () => this.handleSearch());
        document.getElementById('ownerFilter').addEventListener('change', () => this.handleSearch());
        document.getElementById('clearFilters').addEventListener('click', () => this.clearFilters());

        // Set up navigation
        document.getElementById('backToNotes').addEventListener('click', () => this.showDashboard());
        document.getElementById('newNoteBtn').addEventListener('click', () => this.showNoteEditor());
        document.getElementById('createNoteLink').addEventListener('click', (e) => {
            e.preventDefault();
            this.showNoteEditor();
        });

        // Set up note form
        document.getElementById('noteForm').addEventListener('submit', (e) => this.handleNoteSubmit(e));
        document.getElementById('cancelEdit').addEventListener('click', () => this.showDashboard());

        // Set up share users input
        document.getElementById('shareWithUsers').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const username = e.target.value.trim();
                const permission = document.getElementById('sharePermissionSelect').value;
                if (username) {
                    this.addUserToShareList(username, permission);
                    e.target.value = '';
                }
            }
        });

        // Set up note actions
        document.getElementById('editNoteBtn').addEventListener('click', () => {
            this.showNoteEditor(this.currentNote?.id);
        });
        document.getElementById('deleteNoteBtn').addEventListener('click', () => this.handleNoteDelete());
        document.getElementById('shareNoteBtn').addEventListener('click', () => {
            sharingManager.showShareModal(this.currentNote);
        });
    }
}

// Create global notes manager instance
const notesManager = new NotesManager();