import sqlite3
import shutil
import tempfile
from pathlib import Path

import pytest


SCHEMA_SQL = """
CREATE TABLE Entries
(
p_uuid PRIMARY KEY NOT NULL,
p_type,
p_location,
p_lastAccess,
p_modificationTime,
p_isArchived,
p_titles_0_nominal,
p_titles_0_collation,
p_titles_0_pronunciation,
j_titles,
p_titleCount,
p_credits_0_name_collation,
j_credits,
p_creditCount,
j_collections,
p_collectionCount,
j_members,
p_memberCount,
p_lastAccessedPosition,
p_publicationDate,
p_expirationDate,
p_publisher,
p_isDRMProtected,
p_isVisibleInHome,
p_isLatestItem,
p_isDownloading,
p_isUpdateAvailable,
p_virtualCollectionCount,
p_languages_0,
j_languages,
p_languageCount,
p_mimeType,
p_cover,
p_thumbnail,
p_diskUsage,
p_cdeGroup,
p_cdeKey,
p_cdeType,
p_version,
p_guid,
j_displayObjects,
j_displayTags,
j_excludedTransports,
p_isMultimediaEnabled,
p_watermark,
p_contentSize,
p_percentFinished,
p_isTestData,
p_contentIndexedState,
p_metadataIndexedState,
p_noteIndexedState,
p_credits_0_name_pronunciation,
p_metadataStemWords,
p_metadataStemLanguage,
p_ownershipType,
p_shareType,
p_contentState,
p_metadataUnicodeWords,
p_homeMemberCount,
j_collectionsSyncAttributes,
p_collectionSyncCounter,
p_collectionDataSetName,
p_originType,
p_pvcId,
p_companionCdeKey,
p_seriesState,
p_totalContentSize REAL,
p_visibilityState,
p_isProcessed,
p_readState,
p_subType
);

CREATE TABLE Series
(
d_seriesId,
d_itemCdeKey,
d_itemPosition,
d_itemPositionLabel,
d_itemType,
d_seriesOrderType,
UNIQUE (d_seriesId, d_itemCdeKey)
);
"""

SEED_BOOKS = [
    ("uuid-book1", "B08BKGYQXW", "EBOK", "Dungeon Crawler Carl: Book 1",
     "/mnt/us/documents/DCC1.kfx", "Matt Dinniman"),
    ("uuid-book2", "B08PBCD9Y7", "EBOK", "Carl's Doomsday Scenario: Book 2",
     "/mnt/us/documents/DCC2.kfx", "Matt Dinniman"),
    ("uuid-book3", "B08V4QSV6W", "EBOK", "The Dungeon Anarchist's Cookbook: Book 3",
     "/mnt/us/documents/DCC3.kfx", "Matt Dinniman"),
    ("uuid-book4", "B09DD17H3N", "EBOK", "The Gate of the Feral Gods: Book 4",
     "/mnt/us/documents/DCC4.kfx", "Matt Dinniman"),
    ("uuid-book5", "B071GN8Y4G", "EBOK", "Legionnaire: Galaxy's Edge Book 1",
     "/mnt/us/documents/Legionnaire.kfx", "Jason Anspach"),
]


def create_test_db(path):
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA_SQL)
    for uuid, cde_key, cde_type, title, location, author in SEED_BOOKS:
        credits_json = f'[{{"name":"{author}","roleType":"author"}}]'
        conn.execute(
            "INSERT INTO Entries (p_uuid, p_type, p_cdeKey, p_cdeType, "
            "p_titles_0_nominal, p_titles_0_collation, p_titles_0_pronunciation, "
            "j_titles, p_titleCount, "
            "j_credits, p_credits_0_name_collation, p_credits_0_name_pronunciation, p_creditCount, "
            "p_location, p_isVisibleInHome, p_isArchived, p_seriesState, "
            "p_isLatestItem, p_isTestData, p_contentState, p_ownershipType, "
            "p_originType, p_visibilityState, p_isProcessed, "
            "p_contentIndexedState, p_noteIndexedState, "
            "p_collectionSyncCounter, p_collectionDataSetName, "
            "p_subType, j_languages, p_languageCount, p_percentFinished"
            ") VALUES (?, 'Entry:Item', ?, ?, "
            "?, ?, ?, "
            "?, 1, "
            "?, ?, ?, 1, "
            "?, 1, 0, 1, "
            "1, 0, 0, 0, "
            "0, 1, 1, "
            "2147483647, 0, "
            "0, '0', "
            "0, '[]', 0, 0)",
            (
                uuid, cde_key, cde_type,
                title, title, title,
                f'[{{"display":"{title}","collation":"{title}","language":"en","pronunciation":"{title}"}}]',
                credits_json, author, author,
                location,
            ),
        )
    conn.commit()
    conn.close()


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "cc.db"
    create_test_db(db_path)
    return db_path
