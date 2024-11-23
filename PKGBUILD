#Maintainer: Panda <panda@bredos.org>

pkgname=python-imageforge
pkgver=1.1.0
pkgrel=1
depends=('python>=3.12')
url=""
license=('GPLv3')
arch=('any')
makedepends=('python-setuptools' 'python-pipenv')
pkgdesc="Python library designed for building Linux distribution images"

build() {
    cd $srcdir/..
    python setup.py build
}

package() {
    install -Dm644 $srcdir/../LICENSE $pkgdir/usr/share/licenses/$pkgname/LICENSE
    cd $srcdir/..
    python setup.py install --root=$pkgdir --optimize=1 --skip-build
}