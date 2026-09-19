using System;

namespace MyControlCenter.MyFan;

public class MainOption
{
	private uint _OperatingMode;

	public uint GamingProfileIndex;

	public uint OfficeProfileIndex;

	public uint TurboProfileIndex;

	public uint FanBoostEnable;

	public uint FanSafetyProtectNotify;

	public uint DefaultNotify;

	public DateTime BsodTimestampRestored;

	public int WhisperModeSwitch = 1;

	public int WhisperModeSetting;

	public int WhisperModeMinFps_QUIETER;

	public int WhisperModeMinFps_QUIET;

	public int WhisperModeMinFps_BALANCED;

	public uint OperatingMode
	{
		get
		{
			return _OperatingMode;
		}
		set
		{
			if (value != _OperatingMode)
			{
				_OperatingMode = value;
			}
		}
	}
}
