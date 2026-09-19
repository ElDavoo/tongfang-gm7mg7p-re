using System;
using System.Runtime.InteropServices;

namespace MyControlCenter;

internal static class NativeMethods
{
	[StructLayout(LayoutKind.Sequential, Pack = 4)]
	public struct POWERBROADCAST_SETTING
	{
		public Guid PowerSetting;

		public uint DataLength;

		public byte Data;
	}

	public class PowerSettingGuid
	{
		public Guid AcdcPowerSource { get; } = new Guid("5d3e9a59-e9D5-4b00-a6bd-ff34ff516548");

		public Guid BatteryPercentageRemaining { get; } = new Guid("a7ad8041-b45a-4cae-87a3-eecbb468a9e1");

		public Guid ConsoleDisplayState { get; } = new Guid("6fe69556-704a-47a0-8f24-c28d936fda47");

		public Guid GlobalUserPresence { get; } = new Guid("786E8A1D-B427-4344-9207-09E70BDCBEA9");

		public Guid MonitorPowerGuid { get; } = new Guid("02731015-4510-4526-99e6-e5a17ebd1aea");

		public Guid PowerSavingStatus { get; } = new Guid("E00958C0-C213-4ACE-AC77-FECCED2EEEA5");

		public Guid SessionDisplayStatus { get; } = new Guid("2B84C20E-AD23-4ddf-93DB-05FFBD7EFCA5");

		public Guid SessionUserPresence { get; } = new Guid("3C0F4548-C03F-4c4d-B9F2-237EDE686376");

		public Guid SystemAwaymode { get; } = new Guid("98a7f580-01f7-48aa-9c0f-44352c29e5C0");

		public Guid IdleBackgroundTask { get; } = new Guid(1364996568u, 63284, 5693, 160, 253, 17, 160, 140, 145, 232, 241);

		public Guid PowerSchemePersonality { get; } = new Guid(610108737, 14659, 17442, 176, 37, 19, 167, 132, 246, 121, 183);

		public Guid MinPowerSavings { get; } = new Guid("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c");

		public Guid MaxPowerSavings { get; } = new Guid("a1841308-3541-4fab-bc81-f71556f20b4a");

		public Guid TypicalPowerSavings { get; } = new Guid("381b4222-f694-41f0-9685-ff5bb260df2e");
	}

	public static Guid GUID_CONSOLE_DISPLAY_STATE = new Guid(1877382486, 28746, 18336, 143, 36, 194, 141, 147, 111, 218, 71);

	public const int DEVICE_NOTIFY_WINDOW_HANDLE = 0;

	public const int WM_POWERBROADCAST = 536;

	public const int PBT_POWERSETTINGCHANGE = 32787;

	[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
	public static extern IntPtr GetModuleHandle(string lpModuleName);

	[DllImport("User32", CallingConvention = CallingConvention.StdCall, SetLastError = true)]
	public static extern IntPtr RegisterPowerSettingNotification(IntPtr hRecipient, ref Guid PowerSettingGuid, int Flags);

	[DllImport("User32", CallingConvention = CallingConvention.StdCall, SetLastError = true)]
	public static extern bool UnregisterPowerSettingNotification(IntPtr handle);
}
