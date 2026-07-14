import shutil

import build


def test_built_addon_imports_from_package_vendor(tmp_path):
    package = tmp_path / "ankihub_br"
    shutil.copytree(build.PACKAGE_SOURCE, package)
    vendor = package / "vendor"
    vendor.mkdir(exist_ok=True)
    for module in build.RUNTIME_MODULES:
        (vendor / f"{module}.py").write_text("", encoding="utf-8")

    archive = tmp_path / "ankihub_br.ankiaddon"
    build.write_archive(package, archive)

    build.verify_archive(archive)
