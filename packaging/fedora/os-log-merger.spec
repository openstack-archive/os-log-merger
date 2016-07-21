%global srcname os-log-merger
%global	sum	OpenStack Log Merger

Name:		python-%{srcname}
Version:	1.0.6
Release:	1%{?dist}
Summary:	%{sum}

License:	Apache
URL:		https://github.com/mangelajo/os-log-merger/
Source:         https://pypi.python.org/packages/6f/f1/b2a46907086c29725dd0e2296d6f45e7965670a05b43626abc1c81a098a0/os-log-merger-%{version}.tar.gz


BuildRoot:      %{_tmppath}/%{srcname}-%{version}-build
BuildArch:	noarch
BuildRequires:	python2


%description
A tool designed to take a bunch of openstack logs across different projects, and merge them in a single file, ordered by time entries

%package -n %{srcname}
Summary:	%{sum}
%{?python_provide:%python_provide python2-%{srcname}}

%description -n %{srcname}
A tool designed to take a bunch of openstack logs across different projects, and merge them in a single file, ordered by time entries


%prep
%autosetup -n %{srcname}-%{version}


%build
#%py2_build


%install
%py2_install


%check
%{__python2} setup.py test

%files -n %{srcname}
#%license LICENSE
%doc README.rst
%{python2_sitelib}/*
%{_bindir}/os-log-merger
%{_bindir}/oslogmerger
%{_bindir}/netprobe



%changelog
* Tue Jul 19 2016 dani - 1.0.6-1
- First version of the os-log-merger-package


- 
