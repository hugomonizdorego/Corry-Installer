#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe Corry design preview. Sample disks only; no installer or disk operations.
Requires PySide6. Shares the production QSS, artwork and sidebar QML.
"""
import argparse
import os
import sys
import tempfile
import shutil
import yaml
from pathlib import Path
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from PySide6.QtCore import Qt, QObject, Slot, Property, Signal, QAbstractListModel, QModelIndex, QUrl, QTimer, QEvent
from PySide6.QtGui import QFont, QPixmap
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


class Steps(QAbstractListModel):
    changed = Signal()
    labels = ['Welcome', 'Location', 'Keyboard', 'Software', 'Partitions', 'Account', 'Review', 'Finish']
    def __init__(self):
        super().__init__(); self.step = 0
    def rowCount(self, parent=QModelIndex()): return len(self.labels)
    def roleNames(self): return {Qt.UserRole + 1: b'display'}
    def data(self, index, role):
        return self.labels[index.row()] if index.isValid() and role == Qt.UserRole + 1 else None
    @Property(int, notify=changed)
    def currentStepIndex(self): return self.step
    def go(self, value): self.step = value; self.changed.emit()


class Brand(QObject):
    SidebarTextCurrent = Property(int, lambda self: 2, constant=True)
    SidebarBackgroundCurrent = Property(int, lambda self: 3, constant=True)
    @Slot(int, result=str)
    def styleString(self, value): return ACCENT if value == 2 else TINT
    @Slot(result=str)
    def shortProductName(self): return PRODUCT
    @Property(int, constant=True)
    def ProductLogo(self): return 1
    @Slot(int, result=str)
    def imagePath(self, value): return str(BRAND / 'corry-mark.svg')


class Debug(QObject):
    @Slot()
    def about(self): QMessageBox.information(None, 'Corry design preview', 'Development preview with sample data. Based on Calamares; original Corry branding. No disk access.')


def label(text, size=11, bold=False, color=None):
    item = QLabel(text); item.setWordWrap(True)
    font = item.font(); font.setPointSize(size); font.setBold(bold); item.setFont(font)
    if color: item.setStyleSheet('color:' + color)
    return item


class Preview(QWidget):
    def __init__(self):
        super().__init__(); self.setObjectName('mainApp'); self.setWindowTitle('Corry Installer — Design preview')
        self.resize(1120, 780); self.setMinimumSize(960, 720)
        self.rows = [['/dev/vda1', '512 MiB', 'FAT32', '/boot/efi', 'Keep'],
                     ['/dev/vda2', '72 GiB', 'Btrfs', '/', 'Format'],
                     ['/dev/vda3', '4 GiB', 'Swap', '—', 'Format'],
                     ['Free space', '51.5 GiB', '—', '—', 'Available']]
        self.steps = Steps(); self.brand = Brand(); self.debug = Debug()
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self.sidebar = QQuickWidget(); self.sidebar.setFixedHeight(112)
        self.sidebar.setResizeMode(QQuickWidget.SizeRootObjectToView)
        ctx = self.sidebar.rootContext()
        ctx.setContextProperty('ViewManager', self.steps); ctx.setContextProperty('Branding', self.brand); ctx.setContextProperty('debug', self.debug)
        source = (BRAND / 'calamares-sidebar.qml').read_text()
        source = '\n'.join(line for line in source.splitlines() if not line.startswith('import io.calamares.'))
        component = QQmlComponent(self.sidebar.engine())
        component.setData(source.encode(), QUrl.fromLocalFile(str(BRAND / 'calamares-sidebar.qml')))
        obj = component.create(ctx)
        if not obj: raise RuntimeError('\n'.join(e.toString() for e in component.errors()))
        self.sidebar.setContent(QUrl.fromLocalFile(str(BRAND / 'calamares-sidebar.qml')), component, obj)
        outer.addWidget(self.sidebar)
        right = QVBoxLayout(); right.setContentsMargins(36,16,36,20); right.setSpacing(12); outer.addLayout(right,1)
        top=QHBoxLayout(); top.addWidget(label('INSTALL / '+PRODUCT,9,True)); top.addStretch(1); top.addWidget(label('DESIGN PREVIEW · SAMPLE DATA',9,color='#627a89')); right.addLayout(top)
        self.page=QWidget(); self.layout=QVBoxLayout(self.page); self.layout.setContentsMargins(0,8,0,0);self.layout.setSpacing(18);right.addWidget(self.page,1)
        self.foot = label('Preview only. No disk is read or changed.',9,color='#526a7b'); right.addWidget(self.foot)
        nav=QHBoxLayout(); self.cancel=QPushButton('Close preview');self.cancel.clicked.connect(self.close);nav.addWidget(self.cancel);nav.addStretch()
        self.back=QPushButton('Back');self.back.setObjectName('view-button-back');self.back.clicked.connect(lambda:self.show_step(self.steps.step-1));nav.addWidget(self.back)
        self.next=QPushButton('Next  →');self.next.setObjectName('view-button-next');self.next.clicked.connect(lambda:self.show_step(self.steps.step+1));nav.addWidget(self.next);right.addLayout(nav)
        self.show_step(0)

    def clear(self):
        while self.layout.count():
            item=self.layout.takeAt(0)
            if item.widget(): item.widget().hide(); item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    child=item.layout().takeAt(0)
                    if child.widget():child.widget().hide();child.widget().deleteLater()
        self.next.setEnabled(True)

    def title(self, title, subtitle):
        self.layout.addWidget(label(title,26,True));self.layout.addWidget(label(subtitle,11,color='#526a7b'))

    def show_step(self, step):
        step=max(0,min(step,7));self.steps.go(step);self.clear();self.back.setEnabled(step>0);self.next.setText('Next  →' if step<6 else 'Finish preview')
        if step==0:
            hero=QHBoxLayout(); hero.setSpacing(30)
            text=QVBoxLayout(); text.setSpacing(18)
            text.addWidget(label('SELAMAT DATANG',10,True,color=ACCENT))
            text.addWidget(label('Mulai perjalanan\nbaru Anda.',32,True))
            text.addWidget(label('Pasang '+PRODUCT+' dengan panduan yang jelas, satu langkah setiap saat.',13,color='#74717c'))
            form=QFormLayout();self.lang=QComboBox();self.lang.addItems(['Bahasa Indonesia','English','Português']);form.addRow('Bahasa',self.lang);text.addLayout(form)
            text.addWidget(label('Preferensi  →  Disk & akun  →  Tinjau & pasang',10,True));text.addStretch()
            hero.addLayout(text,1)
            art=QLabel();art.setPixmap(QPixmap(str(BRAND/'slides/welcome.svg')).scaled(520,320,Qt.KeepAspectRatio,Qt.SmoothTransformation));art.setAlignment(Qt.AlignCenter);hero.addWidget(art,1)
            self.layout.addLayout(hero,1)
            card=QFrame();card.setObjectName('corryCard');cl=QVBoxLayout(card);cl.setContentsMargins(20,16,20,16)
            cl.addWidget(label('Anda memegang kendali.',13,True));cl.addWidget(label('Btrfs sebagai pilihan awal. Paket tambahan bersifat opsional. Semua perubahan disk ditampilkan untuk ditinjau sebelum instalasi.',11,color='#74717c'));self.layout.addWidget(card)
        elif step in [1,2]:
            self.title('Make yourself at home.' if step==1 else 'Type the way you know.', 'Choose your location and time zone.' if step==1 else 'Select a keyboard layout and try it below.')
            form=QFormLayout()
            fields=[('Region',['Asia','Europe','Africa']),('Time zone',['Dili','Jakarta','Lisbon'])] if step==1 else [('Keyboard model',['Generic 105-key PC']),('Layout',['English (US)','Portuguese','Indonesian'])]
            for name,values in fields:
                combo=QComboBox();combo.addItems(values);form.addRow(name,combo)
            if step==2:form.addRow('Try your keyboard',QLineEdit())
            self.layout.addLayout(form)
        elif step==3:
            self.title('Aplikasi pilihan Anda.', 'Klik untuk memilih paket tambahan. Klik lagi untuk membatalkan. Sistem dasar dapat dipasang offline jika image lengkap.')
            card=QFrame();card.setObjectName('corryCard');row=QHBoxLayout(card);row.setContentsMargins(18,14,18,14)
            row.addWidget(label('✓  Repositori bertanda tangan dapat diakses\nPaket dan dependensinya akan diunduh sebelum partisi diubah.',11,color=ACCENT),1);row.addWidget(QPushButton('Periksa lagi'));self.layout.addWidget(card)
            for title,description in [('Kantor & dokumen','LibreOffice Writer dan Calc'),('Audio & video','VLC media player'),('Alat pengembangan','Git dan perangkat build Debian')]:
                box=QCheckBox(title+'   ·   '+description);box.setChecked(title=='Kantor & dokumen');self.layout.addWidget(box)
            self.layout.addWidget(label('SIMULASI STATUS REPOSITORI · Pratinjau ini tidak melakukan koneksi atau mengunduh paket.',9,color='#74717c'))
        elif step==4:
            self.title('Give your system a place.', 'Choose a disk, then create or select partitions and assign their roles.')
            self.disk=QComboBox();self.disk.addItems(['Sample virtual disk  ·  /dev/vda  ·  128 GiB']);self.layout.addWidget(self.disk)
            row=QHBoxLayout()
            for text,callback in [('Manual partitions',lambda:None),('Automatic Btrfs layout',self.auto_layout)]:
                button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
            self.layout.addLayout(row)
            self.tree=QTreeWidget();self.tree.setHeaderLabels(['Partition','Size','Filesystem','Mount point','Action']);self.tree.setRootIsDecorated(False);self.tree.header().setSectionResizeMode(QHeaderView.ResizeToContents);self.tree.header().setStretchLastSection(True);self.tree.setAlternatingRowColors(True)
            self.fill_tree();self.tree.itemDoubleClicked.connect(lambda *_:self.edit_partition(False));self.layout.addWidget(self.tree,1)
            row=QHBoxLayout()
            for text,callback in [('New partition',lambda:self.edit_partition(True)),('Edit role',lambda:self.edit_partition(False)),('Remove from plan',self.remove_partition)]:
                button=QPushButton(text);button.clicked.connect(callback);row.addWidget(button)
            row.addStretch();self.layout.addLayout(row)
            self.layout.addWidget(label('Btrfs is the default. EFI uses FAT32. Review every Format or Delete action before installing.',10,color='#526a7b'))
        elif step==5:
            self.title('Your desktop. Your account.', 'Choose a name and a password you will use to sign in.')
            form=QFormLayout();self.name=QLineEdit('Hugo Moniz');self.login=QLineEdit('hugo');self.host=QLineEdit('edukasaun-pc' if 'Edukasaun' in PRODUCT else 'debion-pc');self.password=QLineEdit();self.repeat=QLineEdit()
            for edit in [self.password,self.repeat]:edit.setEchoMode(QLineEdit.Password);edit.textChanged.connect(self.validate_password)
            for text,edit in [('Your name',self.name),('Username',self.login),('Computer name',self.host),('Password',self.password),('Repeat password',self.repeat)]:form.addRow(text,edit)
            self.layout.addLayout(form);self.status=label('Enter matching passwords of at least one character.',10,color='#526a7b');self.layout.addWidget(self.status)
            self.layout.addWidget(label('A one-character password is accepted. A longer password is harder to guess.',10,color='#526a7b'));self.layout.addWidget(QCheckBox('Log in automatically'));self.validate_password()
        elif step==6:
            self.title('One last look.', 'Check your choices carefully before starting a real installation.')
            self.layout.addWidget(label('Location     Asia / Dili\nKeyboard     English (US)\nDisk              /dev/vda · sample virtual disk\nFilesystem   Btrfs, with FAT32 for EFI',12))
            self.layout.addWidget(label('The native installer shows the full operation list and asks for confirmation before writing changes.',11,True))
            self.layout.addWidget(label('This preview stops here and cannot start an installation.',10,color='#526a7b'))
        else:
            self.title('Ready for the next stage.', 'The Corry design preview is complete. Native installation must be tested in a virtual machine.')
            self.next.setEnabled(False)
        self.layout.addStretch()

    def show_slideshow(self):
        self.clear();self.steps.go(6)
        self.slide=QQuickWidget(self.sidebar.engine(), self.page);self.slide.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.slide.setSource(QUrl.fromLocalFile(str(BRAND/'show.qml')))
        if self.slide.status()==QQuickWidget.Error:raise RuntimeError(str(self.slide.errors()))
        self.layout.addWidget(self.slide,1)
        self.progress=QProgressBar();self.progress.setValue(46);self.layout.addWidget(self.progress)
        self.layout.addWidget(label('Memasang sistem · contoh progres, tidak ada disk yang diubah',10,color='#74717c'))
        self.slide.rootObject().onActivate()
        self.next.setEnabled(False)

    def fill_tree(self):
        self.tree.clear()
        for row in self.rows:self.tree.addTopLevelItem(QTreeWidgetItem(row))
        self.tree.setCurrentItem(self.tree.topLevelItem(1))

    def auto_layout(self):
        self.rows=[['/dev/vda1','512 MiB','FAT32','/boot/efi','Format'],['/dev/vda2','123.5 GiB','Btrfs','/','Format'],['/dev/vda3','4 GiB','Swap','—','Format']];self.fill_tree()

    def remove_partition(self):
        index=self.tree.indexOfTopLevelItem(self.tree.currentItem())
        if index>=0:self.rows.pop(index);self.fill_tree()

    def validate_password(self):
        valid=bool(self.password.text()) and self.password.text()==self.repeat.text();self.next.setEnabled(valid)
        self.status.setText('Passwords match. One character or more is accepted.' if valid else 'Enter matching passwords of at least one character.')

    def edit_partition(self, new=False, screenshot=None):
        index=self.tree.indexOfTopLevelItem(self.tree.currentItem())
        selected=self.rows[index] if index>=0 and not new else ['', '20 GiB','Btrfs','/','Format']
        dialog=QDialog(self);dialog.setWindowTitle('Corry — Partition role');dialog.resize(720,570)
        layout=QVBoxLayout(dialog);layout.setContentsMargins(24,24,24,24);layout.setSpacing(16)
        layout.addWidget(label('What will this partition be used for?',20,True))
        layout.addWidget(label('Assign a role, then check its size and filesystem.',11,color='#526a7b'))
        grid=QGridLayout();form=QFormLayout();fs=QComboBox();fs.addItems(['Btrfs','ext4','XFS','FAT32','Swap','ext2','ext3']);fs.setCurrentText(selected[2] if selected[2] in ['Btrfs','ext4','XFS','FAT32','Swap','ext2','ext3'] else 'Btrfs')
        mount=QComboBox();mount.setEditable(True);mount.addItems(['/','/home','/boot/efi','/boot','/var','/tmp','']);mount.setCurrentText(selected[3] if selected[3]!='—' else '')
        hint=label('Required: system files and applications.',10,color='#526a7b')
        def role(path,kind,description):
            if kind:fs.setCurrentText(kind)
            elif fs.currentText()=='Swap':fs.setCurrentText('Btrfs')
            mount.setCurrentText(path);hint.setText(description)
            if new:
                recommended = 512 if path=='/boot/efi' else 1024 if path=='/boot' else 4096 if kind=='Swap' else 20480 if path=='/' else 0
                if recommended:size.setValue(recommended)
        roles=[('Root /','/',None,'Required: system files and applications.'),('Home','/home',None,'Personal files. Keep existing data only when Format is not selected.'),('EFI','/boot/efi','FAT32','UEFI boot files. FAT32, boot flag, recommended 512 MiB.'),('Boot','/boot',None,'Optional kernel partition. Recommended 1 GiB.'),('Swap','','Swap','Virtual memory. No mount point.'),('Var','/var',None,'Optional logs, databases and caches.'),('Tmp','/tmp',None,'Optional temporary files.')]
        for n,(text,path,kind,description) in enumerate(roles):
            button=QPushButton(text);button.clicked.connect(lambda checked=False,p=path,k=kind,d=description:role(p,k,d));grid.addWidget(button,n//4,n%4)
        layout.addLayout(grid);layout.addWidget(hint)
        size=QSpinBox();size.setRange(100,131072);size.setValue(20480);size.setSuffix(' MiB');form.addRow('Size',size);form.addRow('Filesystem',fs);form.addRow('Mount point',mount);layout.addLayout(form)
        format_box=QCheckBox('Format this partition — erase its existing contents');format_box.setChecked(new or selected[4]=='Format');layout.addWidget(format_box)
        warning=label('Changes are added to the plan. No disk is changed in this preview.',10,color='#526a7b');layout.addWidget(warning)
        buttons=QDialogButtonBox(QDialogButtonBox.Cancel|QDialogButtonBox.Save);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        def validate():
            message=''
            if mount.currentText()=='/boot/efi' and fs.currentText()!='FAT32':message='EFI requires FAT32.'
            elif fs.currentText()=='Swap' and mount.currentText():message='Swap has no mount point.'
            elif mount.currentText() and not mount.currentText().startswith('/'):message='Mount point must start with /.'
            warning.setText(message or 'Changes are added to the plan. No disk is changed in this preview.');buttons.button(QDialogButtonBox.Save).setEnabled(not message)
        mount.currentTextChanged.connect(validate);fs.currentTextChanged.connect(validate);validate()
        if screenshot:
            dialog.show();QApplication.processEvents();dialog.grab().save(str(screenshot));dialog.close();return
        if dialog.exec()==QDialog.Accepted:
            row=[selected[0] or 'New partition',str(size.value())+' MiB',fs.currentText(),mount.currentText() or '—','Format' if format_box.isChecked() else 'Keep']
            if new:self.rows.insert(max(0,len(self.rows)-1),row)
            elif index>=0:self.rows[index]=row
            self.fill_tree()


def main():
    global BRAND, PRODUCT, ACCENT, TINT, PREVIEW_APP, PREVIEW_WINDOW
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screenshots',type=Path);parser.add_argument('--distro',choices=['edukasaun','debion'],default='debion');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='corry-preview-') as temp:
        BRAND=Path(temp)/'corry';shutil.copytree(ROOT/'src/branding/corry',BRAND)
        overlay=ROOT/'config/distros'/args.distro
        shutil.rmtree(BRAND/'slides');shutil.copytree(overlay/'slides',BRAND/'slides')
        profile=yaml.safe_load((overlay/'profile.yaml').read_text());PRODUCT=profile['name'];ACCENT=profile['accent'];TINT=profile['tint']
        mark=BRAND/'corry-mark.svg';mark.write_text(mark.read_text().replace('#6445a4',ACCENT))
        app=QApplication(sys.argv[:1]);app.setStyle('Fusion');app.setFont(QFont('DejaVu Sans',10));app.setStyleSheet((BRAND/'stylesheet.qss').read_text().replace('#6445a4',ACCENT).replace('#f0ecf8',TINT))
        window=Preview();window.show()
        PREVIEW_APP=app;PREVIEW_WINDOW=window
        if args.screenshots:
            args.screenshots.mkdir(parents=True,exist_ok=True)
            def capture():
                captures=[(0,'welcome')]
                if args.distro=='debion':captures.extend([(3,'software'),(4,'partitions'),(5,'account')])
                for step,name in captures:
                    window.show_step(step);app.processEvents()
                    if step==5:
                        window.password.setText('a');window.repeat.setText('a');assert window.next.isEnabled()
                        window.repeat.setText('b');assert not window.next.isEnabled()
                        window.repeat.setText('a')
                    app.processEvents();window.grab().save(str(args.screenshots/(args.distro+'-'+name+'.png')))
                window.show_slideshow();app.processEvents()
                slide=window.slide.rootObject();assert slide.property('active')
                slide.advance(1);assert slide.property('currentSlide')==1
                slide.onLeave();assert not slide.property('active');slide.onActivate()
                def capture_slide():
                    window.grab().save(str(args.screenshots/(args.distro+'-slideshow.png')));slide.onLeave();window.close();app.quit()
                QTimer.singleShot(300,capture_slide)
            QTimer.singleShot(300,capture)
        result=app.exec()
        return result


if __name__=='__main__':raise SystemExit(main())
