1. 克隆并进入 AutoBangumi 的 `git` 仓库：

   ```powershell
   git clone https://github.com/EstrellaXD/Auto_Bangumi.git
   cd Auto_Bangumi
   ```

2. 修改 `backend\src\module\api\web.py` 以允许 `DEV_VERSION` 下仍然可以显示 Web UI：

   ```powershell
   ((Get-Content -path .\src\module\api\web.py -Raw) -replace 'if VERSION != "DEV_VERSION":','if True:') | Set-Content -Path .\src\module\api\web.py
   ```

3. 创建一个新的分支，以方便后续更新时与远程 `main` 分支合并：

   ```powershell
   git checkout -b non-docker-deployment
   git commit -a -m "Enable WebUI for dev version"
   ```

4. 新建 `python` 虚拟环境、激活并安装依赖（需保证 `python -V` 打印的版本符合 `Dockerfile` 中的要求，如 `FROM python:3.11-alpine AS APP`）

   ```powershell
   python -m venv env
   .\env\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```


5. 下载 WebUI 并安装：

   ```powershell
   Invoke-WebRequest -Uri "https://github.com/Rewrite0/Auto_Bangumi_WebUI/releases/latest/download/dist.zip" -OutFile "dist.zip"
   Expand-Archive -Path "dist.zip"
   mv dist\* backend\src\templates
   ```

6. 创建 `data` 与 `config` 目录和空白的 `config_dev.json`（如果有必要将这些目录存储在其他位置，建议使用 Junction Directory 链接即可）

   ```powershell
   mkdir backend\src\data
   mkdir backend\src\config
   echo "{}" > backend\src\config\config_dev.json
   ```
   默认情况下，PowerShell 输出文件编码为 `UTF-16LE`，你需要将 `config_dev.json` 的编码格式改为 `UTF-8`。

7. 运行程序测试是否配置正确：

   ```powershell
   cd backend\src
   python main.py
   ```

8. 接下来配置成服务以实现开机自启，以下以 `nssm` 为例：

   ```powershell
   nssm install AutoBangumi (Get-Command python).Source
   nssm set AutoBangumi AppParameters (Get-Item .\main.py).FullName
   nssm set AutoBangumi AppDirectory (Get-Item ..).FullName
   nssm set AutoBangumi Start SERVICE_DELAYED_AUTO_START
   ```

9. [可选] 由于 3.0 版本之前 AutoBangumi 没有修改规则或者批量移动下载位置的功能，可能遇到季名不符合需要 (如《鬼灭之刃 刀匠村篇》被视作一个仅具有一季的独立的影视作品，而不是系列动画的第三季) 或者中途想继续下载但是移出库防止出现在新剧集通知中等情况，可与考虑将下载目录和库目录区分开并用 Junction Directory 相连，这样在管理库时可以随意移动软链接而不影响 AutoBangumi 的工作。比如：
	```powershell
	﻿### Configurations
	$downloadDir = "path\to\download_dir"
	$libraryDir = "path\to\library_dir"
	$logFile = $(Join-Path -Path $download_dir -ChildPath "downloadWatcher.log")
	$subfolderCreationTimeout = 10
	$watcher = New-Object System.IO.FileSystemWatcher
	$watcher.Path = $downloadDir
	$watcher.EnableRaisingEvents = $true  

	function CreateJunction(
		# The path to the folder containing junction targets, e.g. $downloadDir\<ShowName>
		# The junction targets are its subfolders e.g. $downloadDir\<ShowName>\<SeasonName>
		$targetRoot 
	) {
		# The basename of $targetRoot, e.g. <ShowName>
		$targetRootName = Split-Path -Path $targetRoot -Leaf
		# The path the folder where junctions are created, e.g. $libraryDir\<ShowName>
		$junctionRoot = $(Join-Path -Path $libraryDir -ChildPath $targetRootName)
		# Create $junctionRoot if it does not exist
		if (!(Test-Path $junctionRoot)) {
			New-Item -ItemType Directory -Path $junctionRoot
			Add-Content $logFile -Value "[Information] $(Get-Date) New folder created at $junctionRoot mirroring $targetRoot."
		}
		# Wait up to 10 secs for a subfolder to appear in $targetRoot
		# This is because if $targetRoot is newly created the downloader may not have created the subfolder yet
		$junctionTargetList = $(Get-ChildItem -Path $targetRoot -Directory)
		$subfolderWaitCount = 0
		while ($junctionTargetList.Count -eq 0) {
			if ($subfolderWaitCount -ge $subfolderCreationTimeout) {
				Add-Content $logFile -Value "[Warning]     $(Get-Date) No subfolders exist in $targetRoot for junctioning, skipping."
				Return
			}
			Start-Sleep -Seconds 1
			try {
				$junctionTargetList = $(Get-ChildItem -Path $targetRoot -Directory)
			}
			# If $targetRoot is removed/renamed during the wait, skip
			catch [System.IO.DirectoryNotFoundException] {
				Add-Content $logFile -Value "[Warning]     $(Get-Date) $targetRoot is removed/renamed during the wait, skipping."
				Return
			}
			$subfolderWaitCount++
		}
		Get-ChildItem $junctionRoot | Where-Object {$_.LinkType -eq "Junction"} | ForEach-Object {
			# If a junction target is non-existent, remove it
			if (!(Test-Path $_.Target)) {
				Remove-Item $_.FullName
				Add-Content $logFile -Value "[Information] $(Get-Date) Junction at $($_.FullName) is removed because its target $($_.Target) is non-existent."
			}
			else {
				# Remove a junction target from $junctionTargetList if a junction in $junctionRoot is already pointing to it 
				$existingTarget = $_.Target
				$junctionTargetList = $junctionTargetList | Where-Object {$_.FullName -ne $existingTarget}
				Add-Content $logFile -Value "[Debug]       $(Get-Date) $($_.FullName) already exists, skipping."
			}
		}
		# Create junctions for each remaining target in $junctionTargetList
		for ($i = 0; $i -lt $junctionTargetList.Count; $i++) {
			$junctionTarget = $junctionTargetList[$i]
			# The default name for the junction is the name of the junction target it self, e.g. <SeasonName>
			$junctionName = $junctionTarget.Name
			# If a junction with the same name already exists, append the current date to the name, e.g. <SeasonName>-yyyy-MM-dd
			if (Test-Path $(Join-Path -Path $junctionRoot -ChildPath $junctionName)) {
				$junctionName = "$junctionName-$(Get-Date -Format "yyyy-MM-dd")"
				# If the new name is still taken, append a random string generated by taking first 5 chars from New-Guid to the name, e.g. <SeasonName>-yyyy-MM-dd-<RandomString>
				while (Test-Path $(Join-Path -Path $junctionRoot -ChildPath $junctionName)) {
					$junctionName = "$junctionName-$((New-Guid).ToString().Substring(0, 5))"
				}
			}
			# Create the junction
			New-Item -ItemType Junction -Path $(Join-Path -Path $junctionRoot -ChildPath $junctionName) -Value $junctionTarget.FullName
			Add-Content $logFile -Value "[Information] $(Get-Date) New junction created at $(Join-Path -Path $junctionRoot -ChildPath $junctionName) pointing to $junctionTarget."
		}
	}

	$action = {
		# Event arguments, see https://learn.microsoft.com/en-us/dotnet/api/system.io.filesystemeventargs
		$details = $event.SourceEventArgs
		$path = $details.FullPath         # Gets the full path of the affected file or directory.
		$changeType = $details.ChangeType # Gets the change type, e.g. Created, Deleted, Renamed
		Add-Content $logFile -Value "[Debug]       $(Get-Date) $changeType event detected at $path."
		if (!(Test-Path $path -PathType Container)) {
			Add-Content $logFile -Value "[Debug]       $(Get-Date) $name is not mirrored because it is not a folder."
			Return
		}
		# If the directory contains .nomirror file, skip
		if (Test-Path $(Join-Path -Path $path -ChildPath ".nomirror")) {
			Add-Content $logFile -Value "[Debug]       $(Get-Date) $path is not mirrored because it contains .nomirror file."
			Return
		}
		# Process the directory as a root of junction targets
		$targetRoot = $path
		# If the directory is renamed, rename its mirror directory
		if ($changeType -eq [System.IO.WatcherChangeTypes]::Renamed) {
			$oldJunctionRoot = $(Join-Path -Path $libraryDir -ChildPath $details.OldName)
			$newJunctionRoot = $(Join-Path -Path $libraryDir -ChildPath $details.Name)
			if (Test-Path $oldJunctionRoot) {
				Rename-Item -Path $oldJunctionRoot -NewName $details.Name
				Add-Content $logFile -Value "[Information] $(Get-Date) $oldJunctionRoot is renamed to $newJunctionRoot."
			}
			else {
				Add-Content $logFile -Value "[Warning]     $(Get-Date) Junction at $oldJunctionRoot does not exist, skipping."
			}
		}
		# If a directory is modified or newly created, update/create its mirror directory by creating/updating junctions to point to its subfolders
		if ($changeType -eq [System.IO.WatcherChangeTypes]::Changed -or `
			$changeType -eq [System.IO.WatcherChangeTypes]::Renamed -or `
			$changeType -eq [System.IO.WatcherChangeTypes]::Created) {
			CreateJunction $targetRoot
		}
	}    

	Register-ObjectEvent -InputObject $watcher -EventName Created -Action $action
	Register-ObjectEvent -InputObject $watcher -EventName Changed -Action $action
	Register-ObjectEvent -InputObject $watcher -EventName Renamed -Action $action
	while ($true) {Start-Sleep 5}
	```
	上述脚本定义了一个 FileSystemWatcher 来监控下载目录的变化并镜像到库目录，可以用 `nssm` 安装为服务自动运行。如果需要排除一个目录，则只需要在该目录下新建一个名为 `.nomirror` 的文件即可。

