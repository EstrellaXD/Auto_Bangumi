from pathlib import Path


def path_to_module_name(path: Path) -> str:
    """转换路径为模块名"""
    rel_path = path.resolve().relative_to(Path.cwd().resolve())
    # stem: 文件名不带后缀
    if rel_path.stem == "__init__":
        return ".".join(rel_path.parts[:-1])
    else:
        return ".".join(rel_path.parts[:-1] + (rel_path.stem,))

if __name__ == "__main__":
    test_path = Path("module/plugin/model.py")
    print(path_to_module_name(test_path))  # module.plugin.model
