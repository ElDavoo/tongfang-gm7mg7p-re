using System.Runtime.InteropServices;

namespace MyControlCenter.MyFan.FanTable;

[StructLayout(LayoutKind.Sequential, Size = 1)]
public struct TableType
{
	public const uint CPU = 1u;

	public const uint GPU = 2u;
}
