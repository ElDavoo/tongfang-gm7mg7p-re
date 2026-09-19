using System.Runtime.InteropServices;

namespace Define;

public class DefaultDisplayModeParams
{
	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Basic
	{
		public const int Brightness = 90;

		public const int Contrast = 0;

		public const int ColorTemp = 0;

		public const int Red = 0;

		public const int Green = 0;

		public const int Blue = 0;
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Intel
	{
		public const int Brightness = 90;

		public const int Contrast = 50;

		public const int ColorTemp = 4200;

		public const int Red = 128;

		public const int Green = 128;

		public const int Blue = 128;
	}
}
