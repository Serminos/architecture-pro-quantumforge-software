$action = New-ScheduledTaskAction -Execute "D:\GITOfficial\architecture-pro-quantumforge-software\updater\update_index.bat" -WorkingDirectory "D:\GITOfficial\architecture-pro-quantumforge-software\updater"
$trigger = New-ScheduledTaskTrigger -Daily -At 20:10
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "Update Vector Index" -Action $action -Trigger $trigger -Settings $settings -User "$env:USERNAME" -RunLevel Highest