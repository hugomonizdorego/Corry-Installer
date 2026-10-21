<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry 0.1 — pengembangan awal

Corry tetap menggunakan mesin pemasangan Calamares. Iterasi ini menambahkan identitas
visual asli dan profil Debian; ini belum merupakan rilis installer yang telah lolos
uji ISO menyeluruh.

## Alur pengguna

1. **Bahasa:** pilih bahasa pemasang.
2. **Lokasi:** pilih wilayah dan zona waktu. Profil awal memakai Asia/Dili, dapat diganti.
3. **Keyboard:** pilih tata letak dan coba input.
4. **Partisi:** pilih disk dan mode secara sengaja. Tidak ada pilihan hapus disk yang dicentang otomatis.
5. **Akun:** isi identitas dan password; minimal satu karakter, tidak boleh kosong, konfirmasi harus sama.
6. **Ringkasan:** baca seluruh operasi, terutama Format dan Hapus. Konfirmasi akhir tetap wajib.
7. **Pemasangan:** konfigurasi target, initramfs Debian, lalu GRUB. Tombol batal dimatikan saat operasi berjalan.
8. **Selesai:** pilih sendiri apakah ingin memulai ulang.

Bahasa yang sudah tersedia memakai terjemahan upstream. Kalimat baru Corry masih
memakai bahasa Inggris dan perlu siklus penerjemahan tersendiri, termasuk Indonesia/Tetum.

## Filesystem dan titik kait

| Pilihan | Pemakaian | Perilaku iterasi ini |
| --- | --- | --- |
| Btrfs | `/`, `/home`, data Linux | Default; subvolume `@`, `@home`, `@cache`, `@log`; kompresi zstd:1 |
| ext4 | Sistem dan data Linux | Pilihan otomatis dan manual |
| XFS | Sistem/data Linux, file besar | Pilihan otomatis dan manual; tidak menawarkan janji penyusutan partisi |
| FAT32 (`fat32`, VFAT saat mount) | `/boot/efi` | EFI wajib FAT32; tombol EFI memilih FAT32 pada partisi baru dan menandai boot |
| Swap (`linuxswap`) | Memori virtual | Tidak memakai titik kait; default otomatis swap kecil |
| ext2 / ext3 | Kebutuhan kompatibilitas lama | Manual jika alat tersedia |
| JFS / ReiserFS | Kebutuhan lama | Manual hanya jika KPMcore dapat membuatnya dan driver kernel tersedia; ReiserFS tidak dipaksakan |

`/` wajib. `/home`, `/boot`, `/var`, `/tmp` opsional. EFI memakai 512 MiB sebagai
rekomendasi dan 100 MiB sebagai batas minimum profil. Kebutuhan ukuran tetap bergantung
pada isi ISO. Batas penyimpanan awal 20 GiB; sesuaikan dengan ukuran payload sebenarnya.
Profil juga mempertahankan dukungan BIOS bawaan Calamares.

Tombol peran hanya mengubah rencana. Pada partisi baru, Root mulai dari 20 GiB, EFI
512 MiB, Boot 1 GiB dan Swap 4 GiB, dibatasi ruang yang tersedia; ukuran tetap dapat
diganti. Pergantian dari EFI menghapus hanya flag boot yang ditambahkan tombol itu. Mengedit partisi lama tidak otomatis menyalakan
Format. Untuk `/home` yang sudah ada, pastikan Format tidak dipilih dan tetap buat
cadangan data. Subvolume Btrfs bukan partisi terpisah dan bukan mekanisme pencadangan.
Pembuatan snapshot otomatis belum termasuk iterasi ini.

## Dependensi dan integrasi ISO

`tools/install-dependencies.sh runtime` memasang backend Debian dan alat filesystem,
GRUB, initramfs, rsync, squashfs, locale dan launcher. Mode `build` menambahkan compiler,
Qt/KDE, KPMcore dan dependensi pengujian. Jalankan di Debian 12/13, termasuk chroot Cubic
yang sesuai. Script tidak dijalankan secara otomatis saat pengguna mengklik Next.

`tools/build-corry.sh` hanya mengaktifkan modul yang dipakai profil. Setelah build,
jalankan `cmake --install`, kemudian `tools/install-profile.sh`. Script profil menyimpan
salinan konfigurasi sebelumnya dan mendukung `DESTDIR` untuk staging. Isi profil ada di
`config/corry/`; nilai password tidak disimpan di profil atau screenshot.

Pastikan `config/corry/modules/corrycleanup.conf` memakai nama akun live ISO yang tepat
(default Debian live-build: `user`). Modul cleanup hanya menghapus paket live dari target,
tanpa `apt autoremove` atau akses jaringan. Akun live yang berbeda dari akun baru juga
dihapus dari target tanpa menghapus direktori home yang mungkin dipertahankan dari
partisi lama. Ini berlangsung sebelum regenerasi initramfs agar diversion paket
live tidak menghambat `update-initramfs`.

Profil memakai grup `sudo` bawaan Debian dan menonaktifkan password root terpisah.
Login otomatis tidak dicentang. Kebijakan perubahan password setelah instalasi tetap
mengikuti sistem yang dipasang; password pendek tidak mengubah konfigurasi PAM.

Bootloader memakai direktori EFI `debian` untuk paket GRUB Debian standar. Nama menu
mengikuti `/etc/os-release`. Secure Boot dan enkripsi penuh belum tervalidasi; enkripsi
otomatis belum ditawarkan. Jangan menganggap keduanya sudah siap rilis.

## Pengujian

Sudah dilakukan dalam lingkungan pengembangan ini:

- Pemeriksaan sintaks C++17 terhadap tiga implementasi dialog/helper partisi dengan header Qt5/KPMcore asli.
- Validasi profil terhadap schema modul, pemeriksaan urutan job, cleanup target dan kasus image hilang.
- Pemeriksaan shell serta staging profil, termasuk path image yang mengandung spasi.
- Rendering Qt preview dan pengujian Next untuk password `a`/`a` diterima, `a`/`b` ditolak.
- Pemeriksaan visual empat screenshot pratinjau setelah rendering.

Ditambahkan untuk CI: build Debian 12/13, `userstest` (termasuk password satu karakter,
konfirmasi salah, kosong dan karakter Unicode), serta `corrypartitiontest` untuk tombol
EFI/Swap/Root, flag boot, mount duplikat, dan perlindungan Format partisi lama.

Build/link native lengkap dan eksekusi tes C++ belum berhasil dilakukan secara lokal:
sebagian dependensi Qt dari mirror lingkungan tidak dapat diunduh. Hasil CI harus
memverifikasi build sebelum pengujian ISO. Screenshot adalah pratinjau Qt dengan data
contoh, bukan screenshot pemasangan native atau hasil boot.

Matriks VM yang harus diselesaikan sebelum rilis:

| Skenario | Pemeriksaan |
| --- | --- |
| UEFI + GPT, hapus disk | Btrfs, EFI FAT32, swap, reboot sukses |
| BIOS + MBR/GPT | bootloader dan partisi BIOS boot yang sesuai |
| Manual + `/home` lama | simpan data tanpa Format, login akun baru |
| ext4 / XFS | pilihan filesystem, fstab, boot sukses |
| Disk lebih dari satu | disk target, partisi EFI dan bootloader konsisten |
| Offline | pemasangan tanpa download; semua dependensi dari ISO |
| Password satu karakter | login, sudo, reboot; bukan hanya validasi formulir |
| Kegagalan pemasangan | pesan error, log, dan pelepasan mount |
| Layar 1024×768 / HiDPI | sidebar bisa digulir; dialog tidak terpotong |

## Screenshot

- `screenshots/corry-welcome.png`
- `screenshots/corry-partitions.png`
- `screenshots/corry-partition-role.png`
- `screenshots/corry-account.png`

Semuanya dirender dari `tools/preview.py`, yang berbagi QSS, sidebar QML dan artwork
produksi. Isi halaman preview adalah storyboard untuk ditinjau. Native tetap memakai
halaman dan validasi Calamares, dengan tombol peran baru pada dialog partisinya.
