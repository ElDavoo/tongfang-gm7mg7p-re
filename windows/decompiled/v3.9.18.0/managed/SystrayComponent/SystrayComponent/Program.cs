using System;

namespace SystrayComponent
{
	internal static class Program
	{
		[STAThread]
		private unsafe static void Main()
		{
			*(_003F*)(IntPtr)/*Error near IL_0001: Stack underflow*/ = /*Error near IL_0001: Stack underflow*/;
			_ = *(short*)(int)(uint)/*Error near IL_0002: Stack underflow*/;
			/*Error near IL_0003: Unknown opcode: 0xA9*/;
		}
	}
}
