#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe Corry design preview. Sample disks only; no installer or disk operations.
Requires PySide6. Shares the production QSS, artwork, header and slideshow QML.
"""
import argparse
import os
import sys
import tempfile
import shutil
import yaml
from pathlib import Path
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from PySide6.QtCore import Qt, QObject, Slot, Property, Signal, QAbstractListModel, QModelIndex, QUrl, QTimer
from PySide6.QtGui import QFont
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtQml import QQmlComponent
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QFrame, QProgressBar, QDialog, QDialogButtonBox, QSpinBox, QGridLayout, QCheckBox, QMessageBox)

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'src/branding/corry'
PRODUCT = 'DebION GNU/Linux'
ACCENT = '#6445a4'
TINT = '#f0ecf8'
MUTED = '#4b5563'
# The step labels Calamares shows for the Corry sequence in settings.conf.
STEPS = ['Welcome', 'System check', 'Location', 'Keyboard', 'Partitions', 'Users', 'Summary', 'Install', 'Finish']
WELCOME, CHECK, LOCATION, KEYBOARD, PARTITIONS, USERS, SUMMARY, INSTALL, FINISH = range(len(STEPS))


class Steps(QAbstractListModel):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.step = 0

    def rowCount(self, parent=QModelIndex()):
        return len(STEPS)

    def roleNames(self):
        return {Qt.UserRole + 1: b'display'}

    def data(self, index, role):
        return STEPS[index.row()] if index.isValid() and role == Qt.UserRole + 1 else None

    @Property(int, notify=changed)
    def currentStepIndex(self):
        return self.step

    def go(self, value):
        self.step = value
        self.changed.emit()


class Brand(QObject):
    SidebarTextCurrent = Property(int, lambda self: 2, constant=True)
    SidebarBackgroundCurrent = Property(int, lambda self: 3, constant=True)
    ProductLogo = Property(int, lambda self: 1, constant=True)

    @Slot(int, result=str)
    def styleString(self, value):
        return ACCENT if value == 2 else TINT

    @Slot(result=str)
    def shortProductName(self):
        return PRODUCT

    @Slot(int, result=str)
    def imagePath(self, value):
        return str(BRAND / 'corry-mark.svg')


class Debug(QObject):
    @Slot()
    def about(self):
        QMessageBox.information(None, 'Corry design preview',
                                'Development preview with sample data. Based on Calamares; original Corry branding. No disk access.')


def label(text, size=11, bold=False, color=None, name=None):
    item = QLabel(text)
    item.setWordWrap(True)
    font = item.font()
    font.setPointSize(size)
    font.setBold(bold)
    item.setFont(font)
    if color:
        item.setStyleSheet('color:' + color)
    if name:
        item.setObjectName(name)
    return item


def card(layout_type=QVBoxLayout, margins=(22, 18, 22, 18)):
    frame = QFrame()
    frame.setObjectName('corryCard')
    layout = layout_type(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(10)
    return frame, layout


class Preview(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName('mainApp')
        self.setWindowTitle('Corry Installer — Design preview')
        self.resize(1120, 780)
        self.setMinimumSize(960, 720)
        self.rows = [['/dev/vda1', '300 MiB', 'FAT32', '/boot/efi', 'Keep'],
                     ['/dev/vda2', '72 GiB', 'Btrfs', '/', 'Format'],
                     ['/dev/vda3', '4 GiB', 'Swap', '—', 'Format'],
                     ['Free space', '51.7 GiB', '—', '—', 'Available']]
        self.steps = Steps()
        self.brand = Brand()
        self.debug = Debug()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.header = QQuickWidget()
        self.header.setFixedHeight(116)
        self.header.setResizeMode(QQuickWidget.SizeRootObjectToView)
        ctx = self.header.rootContext()
        ctx.setContextProperty('ViewManager', self.steps)
        ctx.setContextProperty('Branding', self.brand)
        ctx.setContextProperty('debug', self.debug)
        qml = BRAND / 'calamares-sidebar.qml'
        source = '\n'.join(line for line in qml.read_text().splitlines() if not line.startswith('import io.calamares.'))
        component = QQmlComponent(self.header.engine())
        component.setData(source.encode(), QUrl.fromLocalFile(str(qml)))
        obj = component.create(ctx)
        if not obj:
            raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
        self.header.setContent(QUrl.fromLocalFile(str(qml)), component, obj)
        outer.addWidget(self.header)
        right = QVBoxLayout()
        right.setContentsMargins(40, 24, 40, 20)
        right.setSpacing(12)
        outer.addLayout(right, 1)
        self.page = QWidget()
        self.layout = QVBoxLayout(self.page)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)
        right.addWidget(self.page, 1)
        nav = QHBoxLayout()
        note = label('Design preview · sample data · no disk is read or changed', 9, color='#9ca3af')
        note.setWordWrap(False)
        nav.addWidget(note)
        nav.addStretch()
        self.back = QPushButton('Back')
        self.back.setObjectName('view-button-back')
        self.back.clicked.connect(lambda: self.show_step(self.steps.step - 1))
        nav.addWidget(self.back)
        self.next = QPushButton('Next')
        self.next.setObjectName('view-button-next')
        self.next.clicked.connect(lambda: self.show_step(self.steps.step + 1))
        nav.addWidget(self.next)
        self.cancel = QPushButton('Cancel')
        self.cancel.setObjectName('view-button-cancel')
        self.cancel.clicked.connect(self.close)
        nav.addWidget(self.cancel)
        right.addLayout(nav)
        self.show_step(WELCOME)

    def clear(self):
        def discard(layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().hide()
                    item.widget().deleteLater()
                elif item.layout():
                    nested = item.layout()
                    discard(nested)
                    nested.deleteLater()
        discard(self.layout)
        self.next.setEnabled(True)

    def title(self, title, subtitle):
        self.layout.addWidget(label(title, 24, True))
        self.layout.addWidget(label(subtitle, 11, color=MUTED))

    def show_step(self, step):
        step = max(0, min(step, FINISH))
        self.steps.go(step)
        self.clear()
        self.back.setEnabled(0 < step < INSTALL)
        self.back.setVisible(step != INSTALL)
        self.next.setVisible(step != INSTALL)
        self.cancel.setVisible(step not in (INSTALL, FINISH))
        self.next.setText({SUMMARY: 'Install', FINISH: 'Done'}.get(step, 'Next'))
        getattr(self, 'page_' + STEPS[step].lower().replace(' ', '_'))()
        if step != INSTALL:
            self.layout.addStretch()

    def page_welcome(self):
        hero = QHBoxLayout()
        hero.setSpacing(40)
        text = QVBoxLayout()
        text.setSpacing(16)
        text.addStretch()
        text.addWidget(label('Welcome to\n' + PRODUCT, 30, True))
        text.addWidget(label('Choose your language, location and keyboard, prepare a disk and create your account. '
                             'Everything is installed from this computer\'s installation media; no internet connection is needed. '
                             'Nothing on your disks changes until you confirm the final review.', 11, color=MUTED, name='corryHint'))
        language = QComboBox()
        language.addItems(['American English', 'Bahasa Indonesia', 'Português', 'Tetun'])
        row = QHBoxLayout()
        row.addWidget(language, 1)
        for name in ['Support', 'Known issues']:
            row.addWidget(QPushButton(name))
        text.addLayout(row)
        text.addStretch()
        hero.addLayout(text, 5)
        checks, cl = card()
        cl.addWidget(label('SYSTEM CHECK', 9, True, ACCENT, 'corryEyebrow'))
        cl.addWidget(label('This computer is ready.', 15, True))
        for item in ['At least 20 GiB of disk space', 'At least 1 GiB of memory', 'Running with administrator rights',
                     'Connected to a power source', 'Screen is large enough']:
            cl.addWidget(label('✓   ' + item, 11, color='#1d2129'))
        cl.addStretch()
        hero.addWidget(checks, 4)
        self.layout.addLayout(hero, 1)

    def page_system_check(self):
        self.title('Is this computer ready?', 'Corry checks that this computer can run ' + PRODUCT + ' and whether it is online.')
        for item in ['At least 20 GiB of disk space', 'At least 1 GiB of memory', 'Running with administrator rights',
                     'Connected to a power source', 'Screen is large enough', 'Connected to the Internet']:
            self.layout.addWidget(label('✓   ' + item, 11))
        box, cl = card(QHBoxLayout)
        cl.addWidget(label('An internet connection is recommended. When online, Corry repairs broken packages and installs '
                           'the latest updates while installing. Without internet, everything is installed from the '
                           'installation media.', 10), 1)
        cl.addWidget(QPushButton('Check again'))
        self.layout.addWidget(box)

    def form_page(self, title, subtitle, fields, extra=None):
        self.title(title, subtitle)
        box, cl = card()
        form = QFormLayout()
        form.setSpacing(14)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for name, values in fields:
            combo = QComboBox()
            combo.addItems(values)
            form.addRow(name, combo)
        if extra:
            form.addRow(*extra)
        cl.addLayout(form)
        self.layout.addWidget(box)

    def page_location(self):
        self.form_page('Where are you?', 'Choose your time zone, and the language and formats for the installed system.',
                       [('Region', ['Asia', 'Europe', 'America']), ('Zone', ['Dili', 'Jakarta', 'New York']),
                        ('System language', ['American English (en_US.UTF-8)']), ('Numbers and dates', ['American English (en_US.UTF-8)'])])

    def page_keyboard(self):
        self.form_page('Choose a keyboard layout', 'Pick the layout printed on your keyboard, then try it below.',
                       [('Keyboard model', ['Generic 105-key PC']), ('Layout', ['English (US)', 'Portuguese', 'Indonesian']),
                        ('Variant', ['Default'])], ('Try your keyboard', QLineEdit()))

    def page_partitions(self):
        self.title('Where should it be installed?', 'Choose a disk, then let Corry erase it or assign partitions yourself.')
        disk = QComboBox()
        disk.addItems(['Sample virtual disk  ·  /dev/vda  ·  128 GiB'])
        self.layout.addWidget(disk)
        row = QHBoxLayout()
        for text, callback in [('Erase disk (Btrfs)', self.auto_layout), ('Manual partitioning', lambda: None),
                               ('Open GParted', lambda: None)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        row.addStretch()
        self.layout.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(['Partition', 'Size', 'Filesystem', 'Mount point', 'Action'])
        self.tree.setRootIsDecorated(False)
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.fill_tree()
        self.tree.itemDoubleClicked.connect(lambda *_: self.edit_partition(False))
        self.layout.addWidget(self.tree, 1)
        row = QHBoxLayout()
        for text, callback in [('New partition', lambda: self.edit_partition(True)),
                               ('Edit role', lambda: self.edit_partition(False)), ('Remove from plan', self.remove_partition)]:
            button = QPushButton(text)
            button.clicked.connect(callback)
            row.addWidget(button)
        row.addStretch()
        self.layout.addLayout(row)
        self.layout.addWidget(label('Btrfs is the default. EFI uses FAT32. Review every Format or Delete action before installing.', 10, color=MUTED))

    def page_users(self):
        self.title('Create your account', 'Choose a name and a password you will use to sign in.')
        box, cl = card()
        form = QFormLayout()
        form.setSpacing(12)
        self.name = QLineEdit('Hugo Moniz')
        self.login = QLineEdit('hugo')
        self.host = QLineEdit('edukasaun-pc' if 'Edukasaun' in PRODUCT else 'debion-pc')
        self.password = QLineEdit()
        self.repeat = QLineEdit()
        for edit in [self.password, self.repeat]:
            edit.setEchoMode(QLineEdit.Password)
            edit.textChanged.connect(self.validate_password)
        for text, edit in [('Your name', self.name), ('Username', self.login), ('Computer name', self.host),
                           ('Password', self.password), ('Repeat password', self.repeat)]:
            form.addRow(text, edit)
        cl.addLayout(form)
        self.status = label('', 10, color=MUTED)
        cl.addWidget(self.status)
        cl.addWidget(QCheckBox('Log in automatically without asking for the password'))
        self.layout.addWidget(box)
        self.validate_password()

    def page_summary(self):
        self.title('Ready to install', 'Check your choices. Nothing has been changed yet.')
        for heading, lines in [('Location', 'Time zone Asia/Dili · Language American English (en_US.UTF-8)'),
                               ('Keyboard', 'English (US) on a Generic 105-key PC'),
                               ('Partitions', 'Erase /dev/vda (sample virtual disk) · FAT32 EFI 512 MiB · Btrfs / 123.5 GiB · Swap 4 GiB'),
                               ('Account', 'Hugo Moniz (hugo) on ' + ('edukasaun-pc' if 'Edukasaun' in PRODUCT else 'debion-pc'))]:
            box, cl = card(QHBoxLayout, (22, 14, 22, 14))
            name = label(heading, 11, True)
            name.setFixedWidth(130)
            cl.addWidget(name)
            cl.addWidget(label(lines, 11, color=MUTED), 1)
            self.layout.addWidget(box)
        self.layout.addWidget(label('After you press Install, Corry asks once more before writing to the disk.', 11, True))

    def page_install(self):
        self.slide = QQuickWidget(self.header.engine(), self.page)
        self.slide.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.slide.setSource(QUrl.fromLocalFile(str(BRAND / 'show.qml')))
        if self.slide.status() == QQuickWidget.Error:
            raise RuntimeError(str(self.slide.errors()))
        self.layout.addWidget(self.slide, 1)
        self.layout.addWidget(label('Unpacking the system image · 46%', 10, color=MUTED))
        progress = QProgressBar()
        progress.setValue(46)
        self.layout.addWidget(progress)
        self.slide.rootObject().onActivate()

    def page_finish(self):
        hero = QHBoxLayout()
        hero.setSpacing(40)
        text = QVBoxLayout()
        text.setSpacing(16)
        text.addStretch()
        text.addWidget(label('ALL DONE', 9, True, ACCENT, 'corryEyebrow'))
        text.addWidget(label(PRODUCT + '\nis installed.', 30, True))
        text.addWidget(label('Remove the installation media when the computer restarts. Your new system will start from the disk.', 12, color=MUTED))
        text.addWidget(QCheckBox('Restart now'))
        text.addStretch()
        hero.addLayout(text, 1)
        self.layout.addLayout(hero, 1)

    def fill_tree(self):
        self.tree.clear()
        for row in self.rows:
            self.tree.addTopLevelItem(QTreeWidgetItem(row))
        self.tree.setCurrentItem(self.tree.topLevelItem(1))

    def auto_layout(self):
        self.rows = [['/dev/vda1', '300 MiB', 'FAT32', '/boot/efi', 'Format'], ['/dev/vda2', '123.7 GiB', 'Btrfs', '/', 'Format'],
                     ['/dev/vda3', '4 GiB', 'Swap', '—', 'Format']]
        self.fill_tree()

    def remove_partition(self):
        index = self.tree.indexOfTopLevelItem(self.tree.currentItem())
        if index >= 0:
            self.rows.pop(index)
            self.fill_tree()

    def validate_password(self):
        valid = bool(self.password.text()) and self.password.text() == self.repeat.text()
        self.next.setEnabled(valid)
        self.status.setText('Passwords match.' if valid else 'Enter the same password twice. One character or more is accepted.')

    def edit_partition(self, new=False, screenshot=None):
        index = self.tree.indexOfTopLevelItem(self.tree.currentItem())
        selected = self.rows[index] if index >= 0 and not new else ['', '20 GiB', 'Btrfs', '/', 'Format']
        dialog = QDialog(self)
        dialog.setWindowTitle('Corry — Partition role')
        dialog.resize(720, 570)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 28, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(label('What will this partition be used for?', 20, True))
        layout.addWidget(label('Assign a role, then check its size and filesystem.', 11, color=MUTED))
        filesystems = ['Btrfs', 'ext4', 'XFS', 'FAT32', 'Swap', 'ext2', 'ext3']
        grid = QGridLayout()
        form = QFormLayout()
        fs = QComboBox()
        fs.addItems(filesystems)
        fs.setCurrentText(selected[2] if selected[2] in filesystems else 'Btrfs')
        mount = QComboBox()
        mount.setEditable(True)
        mount.addItems(['/', '/home', '/boot/efi', '/boot', '/var', '/tmp', ''])
        mount.setCurrentText(selected[3] if selected[3] != '—' else '')
        hint = label('Required: system files and applications.', 10, color=MUTED)
        size = QSpinBox()

        def role(path, kind, description):
            if kind:
                fs.setCurrentText(kind)
            elif fs.currentText() == 'Swap':
                fs.setCurrentText('Btrfs')
            mount.setCurrentText(path)
            esp.setChecked(path == '/boot/efi')
            hint.setText(description)
            if new:
                recommended = 300 if path == '/boot/efi' else 1024 if path == '/boot' else 4096 if kind == 'Swap' else 20480 if path == '/' else 0
                if recommended:
                    size.setValue(recommended)
        roles = [('Root /', '/', None, 'Required: system files and applications.'),
                 ('Home', '/home', None, 'Personal files. Keep existing data only when Format is not selected.'),
                 ('EFI', '/boot/efi', 'FAT32', 'UEFI boot files. FAT32 with the boot/ESP flags, set automatically. Recommended: 300 MiB; adjust if needed.'),
                 ('Boot', '/boot', None, 'Optional kernel partition. Recommended 1 GiB.'),
                 ('Swap', '', 'Swap', 'Virtual memory. No mount point.'),
                 ('Var', '/var', None, 'Optional logs, databases and caches.'),
                 ('Tmp', '/tmp', None, 'Optional temporary files.')]
        for n, (text, path, kind, description) in enumerate(roles):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, p=path, k=kind, d=description: role(p, k, d))
            grid.addWidget(button, n // 4, n % 4)
        layout.addLayout(grid)
        layout.addWidget(hint)
        size.setRange(100, 131072)
        size.setValue(20480)
        size.setSuffix(' MiB')
        form.addRow('Size', size)
        form.addRow('Filesystem', fs)
        form.addRow('Mount point', mount)
        layout.addLayout(form)
        esp = QCheckBox('Flags: boot, esp (EFI system partition)')
        layout.addWidget(esp)
        format_box = QCheckBox('Format this partition — erase its existing contents')
        format_box.setChecked(new or selected[4] == 'Format')
        layout.addWidget(format_box)
        warning = label('Changes are added to the plan. No disk is changed in this preview.', 10, color=MUTED)
        layout.addWidget(warning)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        def validate():
            message = ''
            if mount.currentText() == '/boot/efi' and fs.currentText() != 'FAT32':
                message = 'EFI requires FAT32.'
            elif fs.currentText() == 'Swap' and mount.currentText():
                message = 'Swap has no mount point.'
            elif mount.currentText() and not mount.currentText().startswith('/'):
                message = 'Mount point must start with /.'
            warning.setText(message or 'Changes are added to the plan. No disk is changed in this preview.')
            buttons.button(QDialogButtonBox.Save).setEnabled(not message)
        mount.currentTextChanged.connect(validate)
        fs.currentTextChanged.connect(validate)
        validate()
        if screenshot:
            roles_buttons = [b for b in dialog.findChildren(QPushButton) if b.text() == 'EFI']
            if roles_buttons:
                roles_buttons[0].click()
            dialog.show()
            QApplication.processEvents()
            dialog.grab().save(str(screenshot))
            dialog.close()
            return
        if dialog.exec() == QDialog.Accepted:
            row = [selected[0] or 'New partition', str(size.value()) + ' MiB', fs.currentText(), mount.currentText() or '—',
                   'Format' if format_box.isChecked() else 'Keep']
            if new:
                self.rows.insert(max(0, len(self.rows) - 1), row)
            elif index >= 0:
                self.rows[index] = row
            self.fill_tree()


def themed(path):
    version = (ROOT / 'VERSION').read_text().strip()
    path.write_text(path.read_text().replace('#6445a4', ACCENT).replace('#f0ecf8', TINT).replace('@CORRY_VERSION@', version))


def main():
    global BRAND, PRODUCT, ACCENT, TINT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots', type=Path)
    parser.add_argument('--distro', choices=['edukasaun', 'debion'], default='debion')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='corry-preview-') as temp:
        BRAND = Path(temp) / 'corry'
        shutil.copytree(ROOT / 'src/branding/corry', BRAND)
        overlay = ROOT / 'config/distros' / args.distro
        shutil.rmtree(BRAND / 'slides')
        shutil.copytree(overlay / 'slides', BRAND / 'slides')
        profile = yaml.safe_load((overlay / 'distro.yaml').read_text())
        PRODUCT, ACCENT, TINT = profile['short-name'], profile['colors']['accent'], profile['colors']['tint']
        # Same substitution as tools/install-profile.sh (tools/corry-branding.py).
        slides = [{k: s.get(k, '') for k in ['image', 'title', 'description']} for s in profile['slides']]
        (BRAND / 'slides/Slides.js').write_text('var slides = ' + __import__('json').dumps(slides) + ';\n')
        for name in ['stylesheet.qss', 'corry-mark.svg', 'calamares-sidebar.qml', 'show.qml', 'SlideControl.qml']:
            themed(BRAND / name)
        app = QApplication(sys.argv[:1])
        app.setStyle('Fusion')
        app.setFont(QFont('Noto Sans', 10))
        app.setStyleSheet((BRAND / 'stylesheet.qss').read_text())
        window = Preview()
        window.show()
        if args.screenshots:
            args.screenshots.mkdir(parents=True, exist_ok=True)

            def save(name):
                app.processEvents()
                window.grab().save(str(args.screenshots / (args.distro + '-' + name + '.png')))

            def capture():
                # The real installer cannot list disks in a container, so the
                # partition pages are the only screenshots taken from this preview.
                window.show_step(PARTITIONS)
                save('05-partitions-preview')
                window.edit_partition(True, args.screenshots / (args.distro + '-06-partition-role-preview.png'))
                window.show_step(USERS)
                window.password.setText('a')
                window.repeat.setText('a')
                assert window.next.isEnabled()
                window.repeat.setText('b')
                assert not window.next.isEnabled()
                window.show_step(INSTALL)
                slide = window.slide.rootObject()
                assert slide.property('active')
                slide.advance(1)
                assert slide.property('currentSlide') == 1
                slide.onLeave()
                assert not slide.property('active')
                slide.onActivate()

                def capture_slide():
                    slide.onLeave()
                    window.close()
                    app.quit()
                QTimer.singleShot(400, capture_slide)
            QTimer.singleShot(400, capture)
        return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
