/**
 * TDD tests for unified note display functionality.
 * Tests that notes shared by user are not duplicated in the dashboard.
 */

describe('NotesManager Unified Display', () => {
    let notesManager;
    let mockApiClient;

    beforeEach(() => {
        // Create mock API client
        mockApiClient = {
            getNotes: jest.fn(),
            getSharedWithMe: jest.fn(),
            getMyShares: jest.fn()
        };

        // Replace global apiClient
        global.apiClient = mockApiClient;

        // Create notes manager instance
        notesManager = new NotesManager();
    });

    describe('loadNotes with unified display', () => {
        it('should not load shared by me notes when owner_filter is all', async () => {
            // Arrange
            const ownedNotes = {
                items: [
                    {
                        id: '1',
                        title: 'My Note',
                        content: 'Content',
                        tags: ['work'],
                        is_shared_by_user: true,
                        share_count: 1,
                        owner_id: 'user1',
                        created_at: '2024-01-01',
                        updated_at: '2024-01-01'
                    }
                ],
                total: 1
            };

            const sharedWithMe = {
                shares: [
                    {
                        note: {
                            id: '2',
                            title: 'Shared Note',
                            content: 'Shared content',
                            tags: ['personal']
                        }
                    }
                ],
                total_count: 1
            };

            mockApiClient.getNotes.mockResolvedValue(ownedNotes);
            mockApiClient.getSharedWithMe.mockResolvedValue(sharedWithMe);
            mockApiClient.getMyShares.mockResolvedValue({ shares: [], total_count: 0 });

            // Act
            await notesManager.loadNotes(1, { owner_filter: 'all' });

            // Assert
            expect(mockApiClient.getNotes).toHaveBeenCalled();
            expect(mockApiClient.getSharedWithMe).toHaveBeenCalled();
            expect(mockApiClient.getMyShares).not.toHaveBeenCalled(); // Should NOT be called for unified display

            // Should only have owned notes and shared with me notes, not shared by me
            expect(notesManager.currentNotes).toHaveLength(2);
            expect(notesManager.currentNotes.some(note => note.note_type === 'owned')).toBe(true);
            expect(notesManager.currentNotes.some(note => note.note_type === 'shared-with-me')).toBe(true);
            expect(notesManager.currentNotes.some(note => note.note_type === 'shared-by-me')).toBe(false);
        });

        it('should load shared by me notes only when explicitly requested', async () => {
            // Arrange
            const sharedByMe = {
                shares: [
                    {
                        note: {
                            id: '1',
                            title: 'My Shared Note',
                            content: 'Content I shared'
                        }
                    }
                ],
                total_count: 1
            };

            mockApiClient.getNotes.mockResolvedValue({ items: [], total: 0 });
            mockApiClient.getSharedWithMe.mockResolvedValue({ shares: [], total_count: 0 });
            mockApiClient.getMyShares.mockResolvedValue(sharedByMe);

            // Act
            await notesManager.loadNotes(1, { owner_filter: 'shared_by_me' });

            // Assert
            expect(mockApiClient.getMyShares).toHaveBeenCalled();
            expect(mockApiClient.getNotes).not.toHaveBeenCalled();
            expect(mockApiClient.getSharedWithMe).not.toHaveBeenCalled();

            expect(notesManager.currentNotes).toHaveLength(1);
            expect(notesManager.currentNotes[0].note_type).toBe('shared-by-me');
        });

        it('should show sharing indicator for owned notes without duplication', async () => {
            // Arrange
            const ownedNotesWithSharing = {
                items: [
                    {
                        id: '1',
                        title: 'My Shared Note',
                        content: 'Content',
                        tags: ['work'],
                        is_shared_by_user: true,
                        share_count: 2,
                        owner_id: 'user1',
                        created_at: '2024-01-01',
                        updated_at: '2024-01-01'
                    }
                ],
                total: 1
            };

            mockApiClient.getNotes.mockResolvedValue(ownedNotesWithSharing);
            mockApiClient.getSharedWithMe.mockResolvedValue({ shares: [], total_count: 0 });

            // Act
            await notesManager.loadNotes(1, { owner_filter: 'all' });

            // Assert
            expect(mockApiClient.getMyShares).not.toHaveBeenCalled();
            expect(notesManager.currentNotes).toHaveLength(1);

            const note = notesManager.currentNotes[0];
            expect(note.is_shared_by_user).toBe(true);
            expect(note.share_count).toBe(2);
            expect(note.note_type).toBe('owned');
        });
    });
});