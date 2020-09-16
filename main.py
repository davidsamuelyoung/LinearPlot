#  Copyright (c) 2020 David Young.
#  All rights reserved.
#

import LinearPlot
import os
import shutil
import requests


def download_git_version():
    git_version = ''

    r = requests.get("https://raw.githubusercontent.com/davidsamuelyoung/LinearPlot/master/LinearPlot.py", stream=True)
    linearplot_downloaded = open("LinearPlot_git.py", "w")
    linearplot_downloaded.write(r.text)
    for line in r.text.split("\n"):
        if "__version__" in line:
            git_version = line[line.find("=") + 2:]
            break
    linearplot_downloaded.close()

    return git_version


def no_updates(git_version):
    if LinearPlot.version_number() == git_version:
        return True
    else:
        return False


if __name__ == '__main__':
    version = download_git_version()
    if no_updates(version):
        LinearPlot.Main()
    else:
        #print("Wrote new code")
        os.remove("LinearPlot.py")
        shutil.copy("LinearPlot_git.py", "LinearPlot.py")
