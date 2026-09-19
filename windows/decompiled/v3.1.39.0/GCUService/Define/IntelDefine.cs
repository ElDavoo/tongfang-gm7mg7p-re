using System.Runtime.InteropServices;

namespace Define;

public class IntelDefine
{
	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Fan
	{
		public const uint Performance = 1u;

		public const uint Standard = 2u;

		public const uint Quiet = 3u;

		public const uint Benchmark = 4u;
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct Cpu
	{
		public const uint P1 = 1u;

		public const uint P2 = 2u;

		public const uint P3 = 3u;

		public const uint Benchmark = 4u;
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct DGpu
	{
		public const uint G1 = 1u;

		public const uint G2 = 2u;

		public const uint G3 = 3u;

		public const uint Benchmark = 4u;
	}

	[StructLayout(LayoutKind.Sequential, Size = 1)]
	public struct SysPowerModeIndex
	{
		public const uint Performance = 1u;

		public const uint Balanced = 2u;

		public const uint BatterySaver = 3u;

		public const uint Benchmark = 4u;
	}
}
