## @file
# This file contains the script to build UniversalPayload
#
# Copyright (c) 2021, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
##

import argparse
import subprocess
import os
import shutil
import sys

def RunCommand(cmd):
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,cwd=os.environ['WORKSPACE'])
    while True:
        line = p.stdout.readline()
        if not line:
            break
        print(line.strip().decode(errors='ignore'))

    p.communicate()
    if p.returncode != 0:
        print("- Failed - error happened when run command: %s"%cmd)
        raise Exception("ERROR: when run command: %s"%cmd)

def BuildUniversalPayload(Args, MacroList):
    BuildTarget = Args.Target
    ToolChain = Args.ToolChain
    ElfToolChain = 'CLANGDWARF'

    EntryModuleInf = os.path.normpath("UefiPayloadPkg/UefiPayloadEntry/UniversalPayloadEntry.inf")
    DscPath = os.path.normpath("UefiPayloadPkg/UefiPayloadPkg.dsc")
    BuildDir = os.path.join(os.environ['WORKSPACE'], os.path.normpath("Build/UefiPayloadPkgX64"))
    FvOutputDir = os.path.join(BuildDir, f"{BuildTarget}_{ToolChain}", os.path.normpath("FV/DXEFV.Fv"))
    EntryOutputDir = os.path.join(BuildDir, f"{BuildTarget}_{ElfToolChain}", os.path.normpath("X64/UefiPayloadPkg/UefiPayloadEntry/UniversalPayloadEntry/DEBUG/UniversalPayloadEntry.dll"))
    PayloadReportPath = os.path.join(BuildDir, "UefiUniversalPayload.txt")
    ModuleReportPath = os.path.join(BuildDir, "UefiUniversalPayloadEntry.txt")

    if "CLANG_BIN" in os.environ:
        LlvmObjcopyPath = os.path.join(os.environ["CLANG_BIN"], "llvm-objcopy")
    else:
        LlvmObjcopyPath = "llvm-objcopy"
    try:
        RunCommand('"%s" --version'%LlvmObjcopyPath)
    except:
        print("- Failed - Please check if LLVM is installed or if CLANG_BIN is set correctly")
        sys.exit(1)

    Defines = ""
    for key in MacroList:
        Defines +=" -D {0}={1}".format(key, MacroList[key])

    #
    # Building DXE core and DXE drivers as DXEFV.
    #
    BuildPayload = f"build -p {DscPath} -b {BuildTarget} -a X64 -t {ToolChain} -y {PayloadReportPath}"
    BuildPayload += Defines
    RunCommand(BuildPayload)
    #
    # Building Universal Payload entry.
    #
    BuildModule = f"build -p {DscPath} -b {BuildTarget} -a X64 -m {EntryModuleInf} -t {ElfToolChain} -y {ModuleReportPath}"
    BuildModule += Defines
    RunCommand(BuildModule)

    #
    # Copy the DXEFV as a section in elf format Universal Payload entry.
    #
    remove_section = '"%s" -I elf64-x86-64 -O elf64-x86-64 --remove-section .upld.uefi_fv %s'%(LlvmObjcopyPath, EntryOutputDir)
    add_section = '"%s" -I elf64-x86-64 -O elf64-x86-64 --add-section .upld.uefi_fv=%s %s'%(LlvmObjcopyPath, FvOutputDir, EntryOutputDir)
    set_section = '"%s" -I elf64-x86-64 -O elf64-x86-64 --set-section-alignment .upld.uefi_fv=16 %s'%(LlvmObjcopyPath, EntryOutputDir)
    RunCommand(remove_section)
    RunCommand(add_section)
    RunCommand(set_section)

    shutil.copy (EntryOutputDir, os.path.join(BuildDir, 'UniversalPayload.elf'))

def main():
    parser = argparse.ArgumentParser(description='For building Universal Payload')
    parser.add_argument('-t', '--ToolChain')
    parser.add_argument('-b', '--Target', default='DEBUG')
    parser.add_argument("-D", "--Macro", action="append", default=["UNIVERSAL_PAYLOAD=TRUE"])
    MacroList = {}
    args = parser.parse_args()
    if args.Macro is not None:
        for Argument in args.Macro:
            if Argument.count('=') != 1:
                print("Unknown variable passed in: %s"%Argument)
                raise Exception("ERROR: Unknown variable passed in: %s"%Argument)
            tokens = Argument.strip().split('=')
            MacroList[tokens[0].upper()] = tokens[1]
    BuildUniversalPayload(args, MacroList)
    print ("Successfully build Universal Payload")

if __name__ == '__main__':
    main()
