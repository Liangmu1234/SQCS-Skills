[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectName,

    [Parameter(Mandatory = $true)]
    [datetime]$MeetingDate,

    [string]$MinutesTemplate,

    [string]$MinutesTemplateName,

    [string]$OutputFileName,

    [string]$ExistingProjectPath,

    [switch]$CreateIfMissing,

    [string]$ProjectRoot = 'D:\文档\00-项目信息',

    [string]$ProjectFolderTemplate,

    [string]$TemplateRepository = 'https://github.com/Liangmu1234/Meeting-Minutes-Template.git',

    [string]$TemplateRepositoryRef = 'main',

    [string]$TemplateCachePath
)

$ErrorActionPreference = 'Stop'

function Get-GitExecutable {
    $git = Get-Command git -ErrorAction SilentlyContinue
    if ($null -eq $git) {
        throw '未找到 git，无法从 GitHub 获取会议纪要模板。请安装 Git 后重试。'
    }

    return $git.Source
}

function Invoke-Git {
    param([string[]]$Arguments)

    $git = Get-GitExecutable
    & $git @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Git 命令执行失败：git $($Arguments -join ' ')"
    }
}

function Get-TemplateRepositoryRoot {
    if ([string]::IsNullOrWhiteSpace($TemplateCachePath)) {
        $TemplateCachePath = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'Codex\Meeting-Minutes-Template'
    }

    if (-not (Test-Path -LiteralPath $TemplateCachePath)) {
        $parent = Split-Path -Path $TemplateCachePath -Parent
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        Invoke-Git @('clone', '--depth', '1', '--branch', $TemplateRepositoryRef, $TemplateRepository, $TemplateCachePath)
        return (Resolve-Path -LiteralPath $TemplateCachePath).Path
    }

    if (-not (Test-Path -LiteralPath (Join-Path $TemplateCachePath '.git') -PathType Container)) {
        throw "模板缓存目录不是 Git 仓库：$TemplateCachePath"
    }

    $git = Get-GitExecutable
    $currentBranch = (& $git -C $TemplateCachePath branch --show-current).Trim()
    if ($currentBranch -ne $TemplateRepositoryRef) {
        throw "模板缓存当前分支为 $currentBranch，不会强制切换。请使用 $TemplateRepositoryRef 分支的独立缓存目录。"
    }

    Invoke-Git @('-C', $TemplateCachePath, 'fetch', '--depth', '1', 'origin', $TemplateRepositoryRef)
    $originCommit = (& $git -C $TemplateCachePath rev-parse "origin/$TemplateRepositoryRef").Trim()
    if ($LASTEXITCODE -ne 0) {
        throw "无法解析远端模板分支：$TemplateRepositoryRef"
    }
    $currentCommit = (& $git -C $TemplateCachePath rev-parse HEAD).Trim()
    if ($currentCommit -eq $originCommit) {
        return (Resolve-Path -LiteralPath $TemplateCachePath).Path
    }

    & $git -C $TemplateCachePath merge-base --is-ancestor HEAD "origin/$TemplateRepositoryRef" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Invoke-Git @('-C', $TemplateCachePath, 'merge', '--ff-only', "origin/$TemplateRepositoryRef")
        return (Resolve-Path -LiteralPath $TemplateCachePath).Path
    }

    # Preserve an existing divergent cache and clone the rewritten remote history separately.
    $snapshotPath = '{0}-{1}' -f $TemplateCachePath, $originCommit.Substring(0, 12)
    if (Test-Path -LiteralPath $snapshotPath) {
        if (-not (Test-Path -LiteralPath (Join-Path $snapshotPath '.git') -PathType Container)) {
            throw "模板快照目录不是 Git 仓库：$snapshotPath"
        }
        $snapshotCommit = (& $git -C $snapshotPath rev-parse HEAD).Trim()
        if ($snapshotCommit -ne $originCommit) {
            throw "模板快照提交不匹配：$snapshotPath"
        }
    }
    else {
        Invoke-Git @('clone', '--depth', '1', '--branch', $TemplateRepositoryRef, $TemplateRepository, $snapshotPath)
    }

    return (Resolve-Path -LiteralPath $snapshotPath).Path
}

function Get-NormalizedProjectName {
    param([string]$Name)

    $value = $Name.Trim().ToLowerInvariant()
    $value = $value -replace '^\d{2,3}-', ''
    $value = $value.Trim('[', ']', '【', '】')
    $value = $value -replace '-\d{2,4}年\d{1,2}月$', ''
    $value = $value -replace '[\s_\-—–·・（）()\[\]【】]', ''
    return $value
}

function Get-ProjectCandidates {
    param(
        [string]$Root,
        [string]$Name
    )

    $needle = Get-NormalizedProjectName -Name $Name
    if ([string]::IsNullOrWhiteSpace($needle)) {
        throw '项目名称归一化后为空，无法搜索。'
    }

    return @(
        Get-ChildItem -LiteralPath $Root -Directory -Recurse |
            Where-Object {
                $_.Parent -and
                $_.Parent.Name -match '^Q[1-4]$' -and
                $_.Name -notmatch '项目模板' -and
                (Get-NormalizedProjectName -Name $_.Name).Contains($needle)
            }
    )
}

function Get-NextProjectPrefix {
    param([string]$QuarterPath)

    $numbers = @(
        Get-ChildItem -LiteralPath $QuarterPath -Directory |
            ForEach-Object {
                if ($_.Name -match '^(?<num>\d{2})-') {
                    [int]$Matches['num']
                }
            }
    )

    if ($numbers.Count -eq 0) {
        return '00'
    }

    return (($numbers | Measure-Object -Maximum).Maximum + 1).ToString('00')
}

function Get-UniqueOutputPath {
    param(
        [string]$Directory,
        [string]$FileName
    )

    $candidate = Join-Path $Directory $FileName
    if (-not (Test-Path -LiteralPath $candidate)) {
        return $candidate
    }

    $base = [System.IO.Path]::GetFileNameWithoutExtension($FileName)
    $extension = [System.IO.Path]::GetExtension($FileName)
    for ($index = 2; $index -lt 1000; $index++) {
        $candidate = Join-Path $Directory ("{0} ({1}){2}" -f $base, $index, $extension)
        if (-not (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    throw '无法生成唯一的会议纪要文件名。'
}

$templateRepositoryRoot = $null

if ([string]::IsNullOrWhiteSpace($MinutesTemplate)) {
    if ([string]::IsNullOrWhiteSpace($MinutesTemplateName)) {
        throw '未提供会议纪要模板。请传入 -MinutesTemplateName 使用 GitHub 模板，或传入 -MinutesTemplate 使用用户提供的本地模板。'
    }
    $templateRepositoryRoot = Get-TemplateRepositoryRoot
    $MinutesTemplate = Join-Path $templateRepositoryRoot $MinutesTemplateName
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
    throw "项目信息根目录不存在：$ProjectRoot"
}
if (-not (Test-Path -LiteralPath $MinutesTemplate -PathType Leaf)) {
    throw "会议纪要模板不存在：$MinutesTemplate"
}
if ([System.IO.Path]::GetExtension($MinutesTemplate) -ne '.xlsx') {
    throw '当前流程仅支持 .xlsx 会议纪要模板。'
}

$sourceTemplateHashBefore = (Get-FileHash -LiteralPath $MinutesTemplate -Algorithm SHA256).Hash
$projectPath = $null
$createdProject = $false

if (-not [string]::IsNullOrWhiteSpace($ExistingProjectPath)) {
    $resolvedRoot = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
    $resolvedProject = [System.IO.Path]::GetFullPath($ExistingProjectPath).TrimEnd('\')
    if (-not $resolvedProject.StartsWith($resolvedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw '指定项目目录不在项目信息根目录中。'
    }
    if (-not (Test-Path -LiteralPath $resolvedProject -PathType Container)) {
        throw "指定项目目录不存在：$resolvedProject"
    }
    $projectPath = $resolvedProject
}
else {
    $matches = @(Get-ProjectCandidates -Root $ProjectRoot -Name $ProjectName)
    if ($matches.Count -gt 1) {
        $paths = ($matches.FullName | Sort-Object) -join [Environment]::NewLine
        throw "找到多个可能的项目目录，请明确指定 ExistingProjectPath：$([Environment]::NewLine)$paths"
    }
    if ($matches.Count -eq 1) {
        $projectPath = $matches[0].FullName
    }
}

if ($null -eq $projectPath) {
    if (-not $CreateIfMissing) {
        throw '未找到项目目录。确认项目名称和日期后，使用 -CreateIfMissing 创建。'
    }
    if ([string]::IsNullOrWhiteSpace($ProjectFolderTemplate)) {
        if ($null -eq $templateRepositoryRoot) {
            $templateRepositoryRoot = Get-TemplateRepositoryRoot
        }
        $ProjectFolderTemplate = Join-Path $templateRepositoryRoot '00-[项目模板-XX年XX月]'
    }
    if (-not (Test-Path -LiteralPath $ProjectFolderTemplate -PathType Container)) {
        throw "项目文件夹模板不存在：$ProjectFolderTemplate"
    }

    $yearPath = Join-Path $ProjectRoot $MeetingDate.ToString('yyyy')
    $quarter = [math]::Ceiling($MeetingDate.Month / 3)
    $quarterPath = Join-Path $yearPath ("Q{0}" -f $quarter)
    New-Item -ItemType Directory -Path $quarterPath -Force | Out-Null

    $prefix = Get-NextProjectPrefix -QuarterPath $quarterPath
    $safeProjectName = $ProjectName -replace '[<>:"/\\|?*]', '-'
    $folderName = '{0}-[{1}-{2}年{3}月]' -f $prefix, $safeProjectName, $MeetingDate.ToString('yy'), $MeetingDate.Month
    $projectPath = Join-Path $quarterPath $folderName
    if (Test-Path -LiteralPath $projectPath) {
        throw "目标项目目录已存在，拒绝覆盖：$projectPath"
    }

    Copy-Item -LiteralPath $ProjectFolderTemplate -Destination $projectPath -Recurse
    $requiredProjectDirectories = @(
        '1.借货设备',
        '2.测试用例',
        '3.测试版本MIB&软件及工具',
        '4.环境及拓扑',
        '5.测试工具使用方法',
        '6.测试报告及复盘报告',
        '7.测试日报',
        '8.其他'
    )
    foreach ($directoryName in $requiredProjectDirectories) {
        $directoryPath = Join-Path $projectPath $directoryName
        if (-not (Test-Path -LiteralPath $directoryPath -PathType Container)) {
            throw "项目模板复制不完整，缺少目录：$directoryPath"
        }
    }
    $createdProject = $true
}

$archivePath = Join-Path $projectPath '8.其他'
if (-not (Test-Path -LiteralPath $archivePath -PathType Container)) {
    if ($createdProject) {
        throw "项目模板复制不完整，缺少目录：$archivePath"
    }
    New-Item -ItemType Directory -Path $archivePath | Out-Null
}

if ([string]::IsNullOrWhiteSpace($OutputFileName)) {
    $safeProjectName = $ProjectName -replace '[<>:"/\\|?*]', '-'
    $templateName = [System.IO.Path]::GetFileNameWithoutExtension($MinutesTemplate).Trim()
    $OutputFileName = '{0}-{1}-会议纪要-{2}.xlsx' -f $MeetingDate.ToString('yyyy-MM-dd'), $safeProjectName, $templateName
}
elseif ([System.IO.Path]::GetExtension($OutputFileName) -ne '.xlsx') {
    $OutputFileName = "$OutputFileName.xlsx"
}

$outputPath = Get-UniqueOutputPath -Directory $archivePath -FileName $OutputFileName
Copy-Item -LiteralPath $MinutesTemplate -Destination $outputPath

$sourceTemplateHashAfter = (Get-FileHash -LiteralPath $MinutesTemplate -Algorithm SHA256).Hash
if ($sourceTemplateHashBefore -ne $sourceTemplateHashAfter) {
    throw '会议纪要模板哈希发生变化，已停止流程。'
}

[pscustomobject]@{
    project_name = $ProjectName
    meeting_date = $MeetingDate.ToString('yyyy-MM-dd')
    project_path = $projectPath
    project_created = $createdProject
    archive_path = $archivePath
    source_template = (Resolve-Path -LiteralPath $MinutesTemplate).Path
    source_template_sha256 = $sourceTemplateHashAfter
    template_repository = if ($null -ne $templateRepositoryRoot) { $TemplateRepository } else { $null }
    template_repository_ref = if ($null -ne $templateRepositoryRoot) { $TemplateRepositoryRef } else { $null }
    template_repository_commit = if ($null -ne $templateRepositoryRoot) { (& (Get-Command git).Source -C $templateRepositoryRoot rev-parse HEAD).Trim() } else { $null }
    output_path = $outputPath
} | ConvertTo-Json -Depth 4
