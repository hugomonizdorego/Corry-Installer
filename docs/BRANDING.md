<!-- SPDX-License-Identifier: CC0-1.0 -->
# Branding Corry yang mudah diganti

Setiap distro mempunyai folder mandiri: `config/distros/edukasaun/` atau
`config/distros/debion/`. Mesin instalasi tidak perlu diubah untuk mengganti nama,
warna atau media. Tema DebION memakai teal/slate; Edukasaun memakai hijau/slate.

| File/folder | Isi yang dapat diganti |
| --- | --- |
| `branding.yaml` | Nama, URL, warna, teks welcome/finish, lokasi media, urutan slide, volume |
| `images/` | Logo, poster video dan gambar slideshow; SVG/PNG/JPEG/WebP |
| `video/` | Video welcome lokal; direkomendasikan WebM dengan video VP8 dan audio Vorbis |
| `music/` | Musik instalasi lokal; direkomendasikan Ogg Vorbis, alternatif WAV PCM 16-bit |
| `software.yaml` | Paket wajib dan grup aplikasi opsional; nama paket dari repo distro |

Contoh bagian yang biasanya diedit dalam `branding.yaml`:

```yaml
product:
  name: Nama OS Anda
  logo: images/logo.svg
welcome:
  title: Selamat datang.
  description: Pasang {product} dengan mudah.
  image: images/welcome.svg
  video: video/welcome.webm
  videoAutoplay: false
  videoMuted: true
installation:
  eyebrow: MENYIAPKAN SISTEM ANDA
  music: music/installation.ogg
  musicEnabled: true
  musicVolume: 20
  slideInterval: 9000
  slides:
    - image: images/work.svg
      title: Ruang kerja Anda
      description: Aplikasi dan dokumen Anda, di {product}.
```

Ini potongan konfigurasi; salin folder contoh lengkap agar bagian `palette` dan
`finish` tetap tersedia. Teks `{product}` diganti dengan nama OS. Pakai path relatif
di dalam folder branding; URL streaming, path absolut dan symlink keluar ditolak.
Teks kustom tampil sebagaimana ditulis; terjemahan otomatis teks branding belum tersedia.

## Mengganti media dan mengaktifkan profil

1. Taruh media milik distro di folder `images`, `video` atau `music`.
2. Edit path/nama/teks/warna di `branding.yaml`; edit `software.yaml` jika perlu.
3. Validasi, lihat pratinjau, lalu pasang profil ke root ISO.

```bash
python3 tools/branding.py --source config/distros/debion
python3 tools/preview.py --distro debion
DESTDIR=/tmp/debion-root bash tools/install-profile.sh --distro debion
```

Untuk distro ketiga, salin satu folder contoh lengkap dan gunakan folder tersebut:

```bash
cp -a config/distros/debion /tmp/my-os-brand
# Edit /tmp/my-os-brand/branding.yaml dan medianya.
python3 tools/preview.py --branding /tmp/my-os-brand
DESTDIR=/tmp/my-os-root bash tools/install-profile.sh \
  --distro my-os --branding /tmp/my-os-brand
```

Script memvalidasi media dengan `ffprobe`, lalu menghasilkan `branding.desc`, QSS,
`Brand.js` dan konfigurasi welcome/finish/chooser. Validasi selesai sebelum profil
aktif disentuh. File hasil di `/etc/calamares` bukan sumber yang diedit; perubahan
berikutnya dilakukan pada folder branding lalu profil dipasang ulang. Profil lama
pada root tujuan dicadangkan sebelum penggantian.

## Format video dan musik

Build Debian 12 memakai Qt5/GStreamer; Debian 13 memakai Qt6. Dependensi multimedia,
plugin codec dan FFmpeg dipasang oleh `tools/install-dependencies.sh`. WebM VP8 dan
Ogg Vorbis merupakan format contoh yang diuji di kedua build. MP4/H.264, VP9, Opus,
MP3 dan FLAC juga dikenali validator, tetapi dukungan pemutaran tetap bergantung
pada backend/codec distro. Gunakan format contoh untuk hasil yang konsisten.

Konversi file sumber tanpa menimpa file lama:

```bash
bash tools/convert-media.sh video /path/intro.mp4 /tmp/welcome.webm
bash tools/convert-media.sh music /path/music.wav /tmp/installation.ogg
```

Welcome mempunyai Play/Pause dan Sound on/off; default tidak autoplay dan suaranya
mati. `video: ""` menonaktifkan video dan tetap menampilkan poster. File video hilang,
rusak atau codec yang gagal di sesi live menampilkan status tidak tersedia tanpa
menghalangi navigasi. Media yang rusak ditolak lebih awal saat profil dikompilasi.

Musik berjalan hanya selama fase eksekusi instalasi, dapat dinonaktifkan atau diatur
volumenya, dan berhenti saat halaman eksekusi ditinggalkan, termasuk selesai/gagal.
`music: ""` menghapus musik; `musicEnabled: false` memulai dalam keadaan tidak aktif.
Tanpa perangkat audio, installer tetap dapat digunakan. Volume awal `20` berarti 20%.

Slideshow mempunyai Previous/Next/Pause. Jeda slide tidak menjeda musik; kontrol
musik berdiri sendiri. Interval slide antara 3000 dan 120000 milidetik.

## Software dan halaman selesai

Grup software dipilih dengan satu klik dan dibatalkan dengan klik berikutnya.
Tidak ada aplikasi tambahan dipilih secara default. Tombol Skip menghapus semua
pilihan; pemasangan offline tetap membutuhkan image dasar yang lengkap. APT
menyelesaikan unduhan dependensi sebelum partisi ditulis dan memeriksa hasil
pemasangan setelah unpack. Katalog frontend dan backend berasal dari file yang sama.

Halaman akhir memilih **tetap mencoba sesi live** secara default. Memilih restart
belum menjalankan reboot; reboot dijalankan saat pengguna menekan Done/Selesai
atau menutup installer setelah memilih restart. Jika instalasi gagal, reboot dari
halaman akhir dinonaktifkan. Teks kedua pilihan dapat diubah pada bagian `finish`.

## Aset contoh dan lisensi

Logo/ilustrasi Corry dan dua video serta musik demo adalah karya original yang
disediakan dengan **CC0-1.0**. Video enam detik dan musik instrumental 16 detik
merupakan placeholder yang dapat langsung diputar dan diganti dengan media distro.
Sumber pembuat demo ada di `tools/make-demo-media.py`. Tidak ada lagu atau gambar
Linux Mint/Microsoft yang disalin. Berkas lisensi upstream tetap dipertahankan.

Ganti media dengan materi yang Anda miliki atau berlisensi sesuai distribusi OS.
Referensi API multimedia: [Qt Multimedia](https://doc.qt.io/qt-6/qtmultimedia-index.html).
