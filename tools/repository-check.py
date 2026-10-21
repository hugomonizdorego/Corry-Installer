#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from apt_support import check_repositories

if __name__ == '__main__':
    try:
        check_repositories()
    except (OSError, ValueError, RuntimeError):
        print('Repositori belum siap. Periksa internet, tanggal sistem, alamat dan kunci repositori, lalu coba lagi. Anda dapat melanjutkan tanpa paket tambahan jika image dasar lengkap.')
        raise SystemExit(1)
    print('Repositori bertanda tangan dapat diakses. Paket tambahan akan diperiksa dan diunduh sebelum partisi diubah.')
