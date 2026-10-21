#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Safe Corry design preview. Sample disks only; no installer or disk operations.
Requires PySide6. Shares the production QSS, artwork and sidebar QML.
"""
import argparse
import os
import sys
from pathlib import Path
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from PySide6.QtCore import Qt, QObject, Slot, Property, Signal, QAbstractListModel, QModelIndex, QUrl, QTimer
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtQml import QQmlComponent
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QDialog, QDialogButtonBox, QSpinBox, QGridLayout, QCheckBox, QMessageBox)

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / 'src/branding/corry'


class Steps(QAbstractListModel):
    changed = Signal()
    labels = ['Welcome', 'Location', 'Keyboard', 'Partitions', 'Account', 'Review', 'Finish']
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
        self.resize(1080, 720); self.setMinimumSize(860, 640)
        self.rows = [['/dev/vda1', '512 MiB', 'FAT32', '/boot/efi', 'Keep'],
                     ['/dev/vda2', '72 GiB', 'Btrfs', '/', 'Format'],
                     ['/dev/vda3', '4 GiB', 'Swap', '—', 'Format'],
                     ['Free space', '51.5 GiB', '—', '—', 'Available']]
        self.steps = Steps(); self.brand = Brand(); self.debug = Debug()
        outer = QHBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self.sidebar = QQuickWidget(); self.sidebar.setFixedWidth(220)
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
        right = QVBoxLayout(); right.setContentsMargins(30,20,30,20); right.setSpacing(15); outer.addLayout(right,1)
        top=QHBoxLayout(); top.addWidget(label('CORRY INSTALLER',10,True)); top.addStretch(); top.addWidget(label('DESIGN PREVIEW · SAMPLE DATA',9,color='#627a89')); right.addLayout(top)
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
        step=max(0,min(step,6));self.steps.go(step);self.clear();self.back.setEnabled(step>0);self.next.setText('Next  →' if step<5 else 'Finish preview')
        if step==0:
            self.title('A fresh start, at your pace.', 'Welcome to Corry. We will guide you through a few clear steps to set up your desktop.')
            art=QLabel();art.setPixmap(QPixmap(str(BRAND/'welcome.svg')));art.setAlignment(Qt.AlignCenter);self.layout.addWidget(art)
            form=QFormLayout();self.lang=QComboBox();self.lang.addItems(['English','Bahasa Indonesia','Português']);form.addRow('Installer language',self.lang);self.layout.addLayout(form)
            self.layout.addWidget(label('1. Choose your preferences     2. Prepare your disk     3. Review and install',10,True))
            self.layout.addWidget(label('Nothing is written to your disk until you confirm installation.',10,color='#526a7b'))
        elif step in [1,2]:
            self.title('Make yourself at home.' if step==1 else 'Type the way you know.', 'Choose your location and time zone.' if step==1 else 'Select a keyboard layout and try it below.')
            form=QFormLayout()
            fields=[('Region',['Asia','Europe','Africa']),('Time zone',['Dili','Jakarta','Lisbon'])] if step==1 else [('Keyboard model',['Generic 105-key PC']),('Layout',['English (US)','Portuguese','Indonesian'])]
            for name,values in fields:
                combo=QComboBox();combo.addItems(values);form.addRow(name,combo)
            if step==2:form.addRow('Try your keyboard',QLineEdit())
            self.layout.addLayout(form)
        elif step==3:
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
        elif step==4:
            self.title('Your desktop. Your account.', 'Choose a name and a password you will use to sign in.')
            form=QFormLayout();self.name=QLineEdit('Hugo Moniz');self.login=QLineEdit('hugo');self.host=QLineEdit('debion-pc');self.password=QLineEdit();self.repeat=QLineEdit()
            for edit in [self.password,self.repeat]:edit.setEchoMode(QLineEdit.Password);edit.textChanged.connect(self.validate_password)
            for text,edit in [('Your name',self.name),('Username',self.login),('Computer name',self.host),('Password',self.password),('Repeat password',self.repeat)]:form.addRow(text,edit)
            self.layout.addLayout(form);self.status=label('Enter matching passwords of at least one character.',10,color='#526a7b');self.layout.addWidget(self.status)
            self.layout.addWidget(label('A one-character password is accepted. A longer password is harder to guess.',10,color='#526a7b'));self.layout.addWidget(QCheckBox('Log in automatically'));self.validate_password()
        elif step==5:
            self.title('One last look.', 'Check your choices carefully before starting a real installation.')
            self.layout.addWidget(label('Location     Asia / Dili\nKeyboard     English (US)\nDisk              /dev/vda · sample virtual disk\nFilesystem   Btrfs, with FAT32 for EFI',12))
            self.layout.addWidget(label('The native installer shows the full operation list and asks for confirmation before writing changes.',11,True))
            self.layout.addWidget(label('This preview stops here and cannot start an installation.',10,color='#526a7b'))
        else:
            self.title('Ready for the next stage.', 'The Corry design preview is complete. Native installation must be tested in a virtual machine.')
            self.next.setEnabled(False)
        self.layout.addStretch()

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
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    app=QApplication(sys.argv[:1]);app.setStyle('Fusion');app.setFont(QFont('DejaVu Sans',10));app.setStyleSheet((BRAND/'stylesheet.qss').read_text())
    window=Preview();window.show()
    if args.screenshots:
        args.screenshots.mkdir(parents=True,exist_ok=True)
        def capture():
            for step,name in [(0,'corry-welcome.png'),(3,'corry-partitions.png'),(4,'corry-account.png')]:
                window.show_step(step);app.processEvents()
                if step==4:
                    window.password.setText('a');window.repeat.setText('a');assert window.next.isEnabled()
                    window.repeat.setText('b');assert not window.next.isEnabled()
                    window.repeat.setText('a')
                app.processEvents();window.grab().save(str(args.screenshots/name))
            window.show_step(3);app.processEvents();window.edit_partition(screenshot=args.screenshots/'corry-partition-role.png')
            app.quit()
        QTimer.singleShot(250,capture)
    return app.exec()


if __name__=='__main__':raise SystemExit(main())
