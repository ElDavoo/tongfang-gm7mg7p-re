namespace Define;

internal static class RamFan1p5_ECSpec
{
	public const ushort ADDR_CPU_FAN_TABLE_TEMP_UP0 = 3840;

	public const ushort ADDR_CPU_FAN_TABLE_TEMP_DOWN0 = 3856;

	public const ushort ADDR_CPU_FAN_TABLE_DUTY0 = 3872;

	public const ushort ADDR_GPU_FAN_TABLE_TEMP_UP0 = 3888;

	public const ushort ADDR_GPU_FAN_TABLE_TEMP_DOWN0 = 3904;

	public const ushort ADDR_GPU_FAN_TABLE_DUTY0 = 3920;

	public const ushort ADDR_RAMFAN1P5_TABLE_STATUS1 = 3933;

	public const ushort ADDR_RAMFAN1P5_TABLE_STATUS2 = 3934;

	public const ushort ADDR_RAMFAN1P5_TABLE_CTRL = 3935;

	public const ushort ADDR_TimAP_TccOffset_Setting = 1926;

	public const ushort ADDR_TimAP_FanSwitchSpeedT100mSec = 1927;
}
