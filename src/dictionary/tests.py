# src\dictionary\tests.py

import os
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from .models import Dictionary

EXTENSIONS = {
    'html_file': 'html', 'opf_file': 'opf', 'jpg_file': 'jpg',
    'mobi_file': 'mobi', 'json_file': 'json', 'zip_file': 'zip',
}
GENERATED_FILE_FIELDS = tuple(EXTENSIONS)


class GeneratedFileCleanupTests(TestCase):
    """Old build artifacts must not pile up on disk when a dictionary is rebuilt."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=self.media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)

        self.dictionary = Dictionary.objects.create(
            name='Test dictionary',
            creator_name='Tester',
            source_file=ContentFile(b'word\tdefinition\n', name='source.txt'),
        )

    def build(self, dictionary, content):
        """Store generated files the same way dictionary_creator does."""
        for field in GENERATED_FILE_FIELDS:
            getattr(dictionary, field).save(
                f'build.{EXTENSIONS[field]}', ContentFile(content), save=False
            )
        dictionary.save()
        return {field: getattr(dictionary, field).path for field in GENERATED_FILE_FIELDS}

    def dictionary_dir_files(self):
        return sorted(os.listdir(os.path.dirname(self.dictionary.source_file.path)))

    def test_creating_dictionary_logs_no_error(self):
        with self.assertNoLogs('dictionary.signals', level='ERROR'):
            Dictionary.objects.create(
                name='Another', creator_name='Tester',
                source_file=ContentFile(b'x\ty\n', name='source.txt'),
            )

    def test_rebuild_removes_previous_generated_files(self):
        first = self.build(self.dictionary, b'v1')
        second = self.build(self.dictionary, b'v2')

        for field in GENERATED_FILE_FIELDS:
            self.assertNotEqual(first[field], second[field])
            self.assertFalse(os.path.exists(first[field]), f'{field} from previous build left on disk')
            self.assertTrue(os.path.exists(second[field]))
        # Source file plus exactly one file per generated field
        self.assertEqual(len(self.dictionary_dir_files()), 1 + len(GENERATED_FILE_FIELDS))
        self.assertTrue(os.path.exists(self.dictionary.source_file.path))

    def test_save_with_unrelated_update_fields_keeps_files(self):
        first = self.build(self.dictionary, b'v1')
        self.dictionary.status = 'processing'
        self.dictionary.save(update_fields=['status', 'updated_at'])

        for path in first.values():
            self.assertTrue(os.path.exists(path))

    def test_saving_stale_instance_does_not_delete_newer_build(self):
        self.build(self.dictionary, b'v1')
        stale = Dictionary.objects.get(pk=self.dictionary.pk)
        second = self.build(self.dictionary, b'v2')

        stale.is_public = True
        stale.save()

        for path in second.values():
            self.assertTrue(os.path.exists(path))

    def test_new_source_file_still_clears_generated_files(self):
        first = self.build(self.dictionary, b'v1')
        old_source = self.dictionary.source_file.path

        self.dictionary.source_file.save('source.txt', ContentFile(b'new\tsource\n'), save=False)
        self.dictionary.save()

        self.assertFalse(os.path.exists(old_source))
        self.assertTrue(os.path.exists(self.dictionary.source_file.path))
        for field, path in first.items():
            self.assertFalse(os.path.exists(path))
            self.assertFalse(getattr(self.dictionary, field))
