using System.Runtime.InteropServices;

namespace Define;

public class GCU2_Define
{
	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct OperatingMode
	{
		public const uint Gaming = 1u;

		public const uint Office = 0u;

		public const uint Turbo = 2u;

		public const uint Benchmark = 3u;
	}
}
