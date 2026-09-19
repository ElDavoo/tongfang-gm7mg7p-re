using System.Runtime.InteropServices;

namespace MyControlCenter.MyFan.FanTable;

[StructLayout(LayoutKind.Sequential, Size = 1)]
public struct FanTable1p5Type
{
	public const int Turbo = 1;

	public const int Gaming = 2;

	public const int Office = 3;
}
