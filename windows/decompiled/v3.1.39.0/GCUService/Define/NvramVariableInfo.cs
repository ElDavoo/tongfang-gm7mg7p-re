namespace Define;

public class NvramVariableInfo
{
	public byte ICpuCoreVoltageOffsetRangeType;

	public int CoreVoltageOffsetMaximum;

	public int CoreVoltageOffsetMinimum;

	public byte ACpuOverClockSupport;

	public uint ACpuFreqValueMaximum;

	public uint ACpuFreqValueMinimum;

	public uint ACpuVoltageValueMaximum;

	public uint ACpuVoltageValueMinimum;

	public byte OverClockRecoveryFlag;

	public byte MemoryOverClockSupport;

	public byte ApUseFlag;
}
