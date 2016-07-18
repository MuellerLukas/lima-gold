pkgname=("lima-gold")
pkgver=1.0.1
pkgrel=1
pkgdesc="A terminal based Jabber MUC client with support for encrypted and invisible messages"
arch=("any")
url="https://github.com/hackyourlife/lima-gold"
license=("Custom")
depends=("python" "python-sleekxmpp" "python-crypto")
source=(client.py encryptim.py main.py rl.py setup.py)
md5sums=("225d06e97466329015814a9ee1c66db6"
         "851a9f27429ca1dd6792cde39b061d2d"
         "8a83ac03a1d980feada258973640b71c"
         "5e1c0e2735ee8750ee2f29e1a4c3eefa"
         "be06c215cf34d5af64287366bcbc48de")

package() {
  cd "$srcdir"
  python setup.py install --root="$pkgdir/" --install-lib /usr/share/lima-gold --optimize=1
  mkdir -p "$pkgdir/usr/bin"
  ln -s /usr/share/lima-gold/main.py "$pkgdir/usr/bin/lima-gold"
  rm "$pkgdir/usr/share/lima-gold/lima_gold-1.0-py3.5.egg-info"
  chmod 0755 "$pkgdir/usr/share/lima-gold/main.py"
}

# vim:set ts=2 sw=2 et: