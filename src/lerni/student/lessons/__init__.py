"""Packaged, reviewed lesson content.

Resources here are loaded through :class:`lerni.student.catalog.PackageLessonCatalog`,
which verifies them against ``lesson_index.toml`` before a student sees anything.
Editing a byte in this directory without regenerating the index and renewing the
affected human reviews will correctly cause loading to fail.
"""
