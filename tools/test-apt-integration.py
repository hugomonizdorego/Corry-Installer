#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real signed APT resolution, download and offline dependency installation.
Runs only in disposable CI containers. dpkg writes exclusively under a temporary
root. No disk devices, mounts, host package installation or network are used.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import tempfile
import types
import yaml
import apt_support as apt


def command(args, **kwargs):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**kwargs)
    if result.returncode:raise RuntimeError(str(args)+'\n'+result.stdout+result.stderr)
    return result.stdout


def main():
    if os.geteuid()!=0:raise SystemExit('Run this integration test as root inside a disposable Debian CI container.')
    with tempfile.TemporaryDirectory(prefix='corry-integration-') as temp:
        root=Path(temp);repo=root/'repository';repo.mkdir()
        architecture=command(['dpkg','--print-architecture']).strip()
        for name,depends in [('corry-fixture-dependency',''),('corry-fixture-app','Depends: corry-fixture-dependency (= 1.0)\n')]:
            package=root/name;(package/'DEBIAN').mkdir(parents=True);(package/'usr/share/corry-test').mkdir(parents=True)
            (package/'DEBIAN/control').write_text(f'Package: {name}\nVersion: 1.0\nArchitecture: all\nMaintainer: Corry Test <test@example.invalid>\n{depends}Description: Isolated Corry integration fixture\n')
            (package/'usr/share/corry-test'/name).write_text('dependency installation verified\n')
            command(['dpkg-deb','--build',str(package),str(repo/(name+'_1.0_all.deb'))])
        packages=command(['dpkg-scanpackages','.','/dev/null'],cwd=repo)
        (repo/'Packages').write_text(packages)
        raw=(repo/'Packages').read_bytes()
        (repo/'Release').write_text(f'Origin: Corry integration fixture\nLabel: Corry integration fixture\nArchitectures: {architecture} all\nSHA256:\n {hashlib.sha256(raw).hexdigest()} {len(raw)} Packages\n')
        keyhome=root/'gnupg';keyhome.mkdir(mode=0o700)
        gpg=['gpg','--batch','--yes','--homedir',str(keyhome),'--pinentry-mode','loopback','--passphrase','']
        command(gpg+['--quick-generate-key','Corry Fixture <test@example.invalid>','rsa2048','sign','0'])
        command(gpg+['--clearsign','--output',str(repo/'InRelease'),str(repo/'Release')])
        payload=root/'payload';(payload/'etc/apt/sources.list.d').mkdir(parents=True);(payload/'usr/share/keyrings').mkdir(parents=True)
        with (payload/'usr/share/keyrings/corry-fixture.gpg').open('wb') as output:
            subprocess.run(gpg+['--export'],stdout=output,stderr=subprocess.DEVNULL,check=True)
        (payload/'etc/apt/sources.list.d/test.sources').write_text(f'Types: deb\nURIs: file:{repo}\nSuites: ./\nSigned-By: /usr/share/keyrings/corry-fixture.gpg\n')
        status=f'Package: linux-image-corry-fixture\nStatus: install ok installed\nArchitecture: {architecture}\nVersion: 1.0\nMaintainer: Corry Test <test@example.invalid>\nDescription: Kernel status fixture; no kernel is installed by this test\n\n'
        (payload/'var/lib/dpkg').mkdir(parents=True);(payload/'var/lib/dpkg/status').write_text(status)
        image=root/'filesystem.squashfs';command(['mksquashfs',str(payload),str(image),'-noappend','-processors','1','-quiet'])
        catalog=root/'software.yaml';catalog.write_text(yaml.safe_dump({'required':[],'groups':[{'id':'fixture','packages':['corry-fixture-app']}]}))
        target=root/'target';shutil.copytree(payload,target)
        (target/'var/log/apt').mkdir(parents=True);(target/'var/lib/dpkg/info').mkdir();(target/'var/lib/dpkg/updates').mkdir()
        gs={'packagechooser_packagechooser':'fixture','rootMountPoint':str(target)}
        calls=[]
        def target_call(args):
            calls.append(args)
            assert args[:2]==['env','DEBIAN_FRONTEND=noninteractive']
            env=os.environ.copy();env['APT_CONFIG']=str(target/args[2].split('=',1)[1].lstrip('/'))
            cache=target/'var/lib/corry/install-cache'
            options=['-o','Dir::Etc='+str(target/'etc/apt'),'-o','Dir::State::status='+str(target/'var/lib/dpkg/status'),'-o','Dir::State::lists='+str(cache/'lists'),'-o','Dir::Cache::archives='+str(cache/'archives'),'-o','Dir::Log='+str(target/'var/log/apt'),'-o','DPkg::Options::=--root='+str(target),'-o','APT::Sandbox::User=root']
            command(['apt-get']+options+args[4:],env=env)
            return 0
        lib=types.SimpleNamespace(globalstorage=types.SimpleNamespace(value=gs.get,insert=gs.__setitem__),job=types.SimpleNamespace(configuration={'image':str(image),'catalog':str(catalog)}),utils=types.SimpleNamespace(target_env_call=target_call))
        prepared=None
        try:
            apt.prepare(lib);prepared=Path(gs['corryPrepared'])
            assert len(list((prepared/'archives').glob('*.deb')))==2,'Both app and its dependency must be downloaded'
            shutil.rmtree(repo)  # Offline installation must work with the source gone.
            apt.install(lib)
            assert (target/'usr/share/corry-test/corry-fixture-app').is_file()
            assert (target/'usr/share/corry-test/corry-fixture-dependency').is_file()
            assert '--no-download' in calls[0]
            assert not prepared.exists()
        finally:
            if prepared:shutil.rmtree(prepared,ignore_errors=True)
        print('PASS: signed repository, image-based dependency resolution, two cached DEBs, source removed, offline target install and apt dependency check.')

if __name__=='__main__':main()
