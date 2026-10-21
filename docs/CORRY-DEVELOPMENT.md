<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry — integrasi Edukasaun OS dan DebION

Ini adalah pengembangan awal Calamares 3.3.15. Mesin pemasangan tetap Calamares;
konfigurasi Debian diadaptasi dari Catalyst dan alur/slideshow mengacu pada fitur
Linux Mint Live Installer. Snapshot konfigurasi Catalyst beserta lisensi ISC disimpan
di `config/upstream/catalyst`. Fork konfigurasi dipelihara di dalam repositori Corry,
bukan fork GitHub terpisah. Logo/gambar dari kedua proyek referensi tidak disalin.

## Dua distro, satu mesin

Build dan install backend Corry, lalu pilih tepat satu profil untuk setiap root ISO:

```bash
sudo bash tools/install-profile.sh --distro edukasaun
sudo bash tools/install-profile.sh --distro debion --image /run/live/medium/live/custom.squashfs
# Staging tanpa mengubah host:
DESTDIR=/tmp/edukasaun-root bash tools/install-profile.sh --distro edukasaun
```

Nama, warna, teks welcome/finish dan path media diatur dalam satu
`config/distros/<id>/branding.yaml`. Gambar berada di `images/`, video di `video/`,
dan musik di `music/`. Ganti file lalu jalankan pemasangan profil lagi. Compiler
memvalidasi media sebelum profil aktif diganti. Folder distro lain dapat dipakai
melalui `--distro my-os --branding /path/brand`. Lihat [panduan branding](BRANDING.md)
untuk contoh konfigurasi dan konversi format. Engine/QML bersama berada di
`src/branding/corry`; kode mesin tidak perlu diduplikasi untuk mengganti OS.

Pakai desktop entry `corry-installer.desktop` sebagai launcher installer bawaan dalam
konfigurasi desktop/live-build distro. Profil tidak membangun ISO dan tidak mengubah
sistem host menjadi Edukasaun atau DebION. Integrator tetap menyiapkan `/etc/os-release`,
kernel, firmware, desktop, login manager serta repository dan keyring distro di payload.

Untuk turunan Debian dengan nomor versi produk sendiri, jalankan kedua script build
menggunakan `CORRY_DEBIAN_VERSION=12` atau `13`, sesuai basis Debian yang sebenarnya.
Dependensi runtime harus dimasukkan sebelum squashfs dikemas. Build source memasang
ke path paket `calamares` Debian; gunakan chroot/mesin pengembangan terpisah sampai
paket Debian Corry khusus tersedia.

## Alur pemasangan dan paket

Menu langkah berada di atas. Halaman aplikasi mempunyai pemeriksaan repositori dan
tombol coba ulang. Pilihan aplikasi memakai klik biasa untuk memilih/membatalkan.
Tidak ada paket tambahan dipilih otomatis. Paket dapat diubah di `software.yaml`;
chooser dan backend memakai katalog yang sama.

1. Launcher memeriksa alat filesystem, GRUB/initramfs dan keberadaan image.
2. Halaman aplikasi memeriksa akses repositori sesi live menggunakan APT dalam folder
   sementara. Status ini mencakup koneksi, metadata dan tanda tangan repositori;
   tidak bergantung pada ping atau layanan pengecekan internet pihak ketiga.
3. Setelah konfirmasi akhir, job `corryprepare` berjalan **sebelum job partisi**.
   Ia membaca status dpkg dari squashfs dan memastikan kernel tercatat terpasang.
   Dependensi dihitung dari status image tersebut, bukan dari paket sesi live.
4. Jika paket wajib sudah ada dan tidak ada tambahan yang dipilih, tidak diperlukan
   akses jaringan. Jika ada paket yang kurang, konfigurasi APT/keyring diambil dari
   image, metadata diverifikasi, dependency disimulasikan, lalu seluruh unduhan diselesaikan.
   Repo tidak dapat diakses, paket tidak tersedia, signature gagal, atau ruang unduhan
   habis menghentikan proses pada tahap ini sebelum perubahan disk dimulai.
   Paket tambahan pada iterasi awal memakai mirror HTTP/HTTPS bertanda tangan;
   sumber media `file:` yang tidak membuat cache unduhan dihentikan sebelum partisi.
5. Setelah unpack, `corrypackages` memeriksa hash cache, memasang dengan
   `--no-download --no-remove`, menjalankan `apt-get check` dan memeriksa status paket
   yang diminta. Kegagalan tidak dilewati. Cache dibersihkan setelah sukses.
6. Cleanup live → initramfs → konfigurasi GRUB → pemasangan bootloader → umount.
   Slideshow lokal berjalan selama fase eksekusi; dapat dijeda dan dipindah manual.
   Musik latar mempunyai pengaturan volume dan aktif/nonaktif, dan berhenti saat
   fase eksekusi ditinggalkan. Welcome mempunyai frame video terpisah.

APT berjalan dengan status/lists/cache terpisah dan hook apt.conf sesi live dimatikan.
Konfigurasi sumber tidak ditulis ulang ke mirror pihak ketiga. Sumber `trusted=yes`
atau `allow-insecure=yes` ditolak untuk unduhan tambahan. Repository distro dalam
image harus cocok dengan basis paket image. Pengunduhan besar membutuhkan ruang
pada penyimpanan sementara sesi live. Pemeriksaan tidak menjamin perangkat keras,
bootloader, listrik atau media penyimpanan tidak akan gagal.

## Partisi dan akun

| Filesystem | Penggunaan |
| --- | --- |
| Btrfs | Default `/`; subvolume `@`, `@home`, `@cache`, `@log`; zstd:1 |
| ext4 / XFS | Pilihan otomatis dan manual |
| FAT32 / VFAT | EFI `/boot/efi`, rekomendasi 512 MiB, minimum profil 100 MiB |
| Swap | Memori virtual; tidak mempunyai titik kait |
| ext2 / ext3 | Manual jika alat tersedia |
| JFS / ReiserFS | Manual hanya jika alat KPMcore dan driver kernel mendukung |

Tombol peran Root, Home, EFI, Boot, Swap, Var dan Tmp mengubah rencana partisi.
Root baru mulai 20 GiB, EFI 512 MiB, Boot 1 GiB, Swap 4 GiB, dibatasi ruang tersedia.
Ukuran dan filesystem tetap dapat diedit. Mengedit partisi lama tidak menyalakan
Format otomatis. Untuk `/home` lama, periksa Format tidak dipilih dan buat cadangan.
Snapshot Btrfs otomatis belum disediakan. Enkripsi otomatis belum ditawarkan.

Password minimal satu karakter, tidak boleh kosong, dan konfirmasi harus sama.
Root password terpisah dimatikan; akun memakai grup sudo. Login otomatis tidak dipilih.
Kebijakan perubahan password setelah instalasi tetap mengikuti PAM sistem target.

Atur `corrycleanup.conf` sesuai nama akun live (default `user`). Cleanup hanya bekerja
di target, menghapus paket live tanpa autoremove, serta menghapus akun live yang
berbeda dari akun baru tanpa menghapus direktori home. Bootloader memakai direktori
EFI `debian` yang diperlukan GRUB Debian standar; nama produk tetap berbeda di UI.

## Verifikasi dan batas rilis

Tes profil memeriksa schema, urutan job, cleanup dan image hilang. Tes perangkat lunak
mencakup offline, pilihan tidak dikenal, repo gagal, hash cache berubah dan kegagalan
pemasangan. Tes integrasi APT membuat repo lokal bertanda tangan dan dua paket contoh
(app + dependensi), membuat squashfs, mengunduh keduanya, menghapus repo, lalu
memasang paket secara offline ke root dpkg sementara. Tes ini tidak memformat disk.

CI membangun backend lengkap untuk Debian 12/Qt5 dan Debian 13/Qt6, menjalankan tes
native password/partisi/packagechooser, pemutaran/decoding media dan kebijakan reboot dan memasang hasil build serta dua profil
ke direktori staging. Build menghasilkan arsip pengembangan per distro dan basis
Debian serta checksum SHA256 di artifact GitHub Actions (disimpan 14 hari). Arsip
untuk pengujian root ISO/chroot dengan dependensi yang cocok, bukan paket Debian
bertanda tangan atau ISO rilis. Hasil run CI terbaru di PR menjadi acuan status build.

Screenshot berasal dari `tools/preview.py`: QML header/video/slideshow, QSS dan artwork
produksi dengan isi halaman storyboard dan data contoh. Status internet/progresnya
simulasi. [Sembilan tahap tiap distro](screenshots/README.md) mencakup welcome sampai
finish. Ini bukan bukti pemasangan ISO maupun hasil reboot.

Sebelum rilis, tuntaskan matriks VM untuk **masing-masing distro**:

| Skenario | Hasil yang harus dibuktikan |
| --- | --- |
| UEFI + GPT / BIOS + MBR/GPT | Partisi tepat, initramfs/GRUB, reboot dan login |
| Btrfs / ext4 / XFS | fstab dan boot sukses |
| Manual + `/home` lama / multi-disk | Data dipertahankan, EFI dan bootloader sesuai disk |
| Offline tanpa tambahan | Semua paket wajib tersedia dari image |
| Online + tambahan / repo mati | Dependensi lengkap, kegagalan berhenti sebelum partisi |
| Password satu karakter | Login dan sudo setelah reboot |
| 1024×768 / HiDPI | Menu, halaman dan dialog dapat digunakan |
| Kegagalan listrik/media/paket | Log dan pelepasan mount dapat diperiksa |

Secure Boot dan enkripsi penuh belum tervalidasi. Tidak ada klaim keberhasilan 100%
sebelum pengujian ISO/boot yang sesuai selesai.
