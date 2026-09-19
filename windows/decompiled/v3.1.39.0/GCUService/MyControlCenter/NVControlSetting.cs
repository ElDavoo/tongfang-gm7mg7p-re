using System.Runtime.InteropServices;

namespace MyControlCenter;

internal class NVControlSetting
{
	public enum AccessFlags : uint
	{
		ACCESS_SCHEME = 16u,
		ACCESS_SUBGROUP,
		ACCESS_INDIVIDUAL_SETTING
	}

	public enum NvControlPanel : byte
	{
		NV_CTRL_AUTOSELECT,
		NV_CTRL_HIGHPERFORMANE
	}

	[DllImport("NVControlSetting.dll")]
	public static extern void SetNVCtrlPanel(byte Status);
}
