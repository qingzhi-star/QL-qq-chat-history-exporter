"""冻结后的管道内核、显式计划导出与更新检测入口。"""
import sys
from qqexport.temporary import cleanup_stale

if __name__=="__main__":
    if sys.argv[1:] == ["--check-updates"]:
        from qqexport import __version__
        from qqexport.updates import print_update_status
        for stream in (sys.stdout, sys.stderr):
            if stream is not None:
                stream.reconfigure(encoding="utf-8", errors="replace")
        raise SystemExit(0 if print_update_status(__version__) else 1)
    if len(sys.argv)==3 and sys.argv[1]=="--scheduled-export":
        from pathlib import Path
        from qqexport.scheduled import run
        raise SystemExit(run(Path(sys.argv[2])))
    cleanup_stale()
    from qqexport.electron_backend import main
    main()
