Name:           insights-core
Version:        3.8.0
Release:        1%{?dist}
Summary:        Insights Core is a data collection and analysis framework.

License:        Apache-2.0
URL:            https://github.com/RedHatInsights/insights-core
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel

Requires: python3

Requires: python3-pyyaml
Requires: python3-requests
Requires: python3-six

%description
Insights Core is a data collection and analysis framework.

%prep
%setup -q -n %{name}-%{version}

%install
rm -rf $RPM_BUILD_ROOT
%{__python3} setup.py install -O1 --root $RPM_BUILD_ROOT
rm -rf $RPM_BUILD_ROOT/usr/bin

%files
# For noarch packages: sitelib
%{python3_sitelib}/*

%changelog
%autochangelog
