# os-log-merger Packaging: RPM

This specfile can be used to build os-log.merger RPM package for Red Hat based distributions. Tested on Fedora 24.

## Local build

### Install build tools
```sh
dnf install @development-tools fedora-packager
```

### Install dependencies
```sh
dnf builddep os-log-merger.spec
```


### Download source files
```sh
spectool --sourcedir --get-files os-log-merger.spec
```

### Build RPM
```sh
rpmbuild -bb os-log-merger.spec
```
