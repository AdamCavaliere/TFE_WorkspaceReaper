import os
import glob

filesout = list()
for root, dirs, files in os.walk('/Users/adam/SynologyDrive/HashiDemos/terraform/TFE_WorkspaceReaper/functions/static/'):
    for file in files:
        filesout.append(os.path.relpath(os.path.join(root,file)))
print(filesout)