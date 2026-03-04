# Fix flex 2.6.4 K&R-style malloc() declaration incompatible with modern GCC.
# lib/malloc.c declares 'void *malloc ()' which newer compilers reject when
# called with an argument. Replace with a proper prototype.
do_configure:prepend:class-nativesdk() {
    sed -i 's/void \*malloc ();/void *malloc (unsigned long);/' ${S}/lib/malloc.c || true
}
