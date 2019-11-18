mkimg - Create nspawn images
============================

`mkimg` is a simple wrapper around [mkosi](https://github.com/systemd/mkosi) that is specifically concerned with
making systemd-nspawn containers on btrfs.  The core concepts behind this program are discussed at the following talks:

* [@scale 2018](https://atscaleconference.com/videos/holding-it-in-scale-the-systemd-tails-on-containers-composable-services-and-runtime-fun-times/)
* [All Systems Go 2019]()

See [mkimg.md](mkimg.md) for help with running `mkimg`