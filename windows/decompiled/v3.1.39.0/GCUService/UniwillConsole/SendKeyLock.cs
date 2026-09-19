using System.Runtime.InteropServices;

namespace UniwillConsole;

public static class SendKeyLock
{
	private const uint KEYEVENTF_EXTENDEDKEY = 1u;

	private const uint KEYEVENTF_KEYUP = 2u;

	[DllImport("user32.dll")]
	private static extern short GetKeyState(int nVirtKey);

	[DllImport("user32.dll")]
	private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, uint dwExtraInfo);

	public static bool GetState(VirtualKeys Key)
	{
		return GetKeyState((int)Key) == 1;
	}

	public static void SetState(VirtualKeys Key1, VirtualKeys Key2, VirtualKeys Key3)
	{
		keybd_event((byte)Key1, 0, 0u, 0u);
		keybd_event((byte)Key2, 0, 0u, 0u);
		keybd_event((byte)Key3, 0, 0u, 0u);
		keybd_event((byte)Key1, 0, 2u, 0u);
		keybd_event((byte)Key2, 0, 2u, 0u);
		keybd_event((byte)Key3, 0, 2u, 0u);
	}
}
