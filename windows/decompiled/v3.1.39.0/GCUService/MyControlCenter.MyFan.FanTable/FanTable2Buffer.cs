namespace MyControlCenter.MyFan.FanTable;

public struct FanTable2Buffer
{
	public uint ID;

	public byte CpuUpT;

	public byte CpuDownT;

	public byte Duty;

	public byte GpuUpT;

	public byte GpuDownT;

	public FanTable2Buffer(uint _id, byte _CpuUpT, byte _CpuDownT, byte _Duty, byte _GpuUpT, byte _GpuDownT)
	{
		ID = _id;
		CpuUpT = _CpuUpT;
		CpuDownT = _CpuDownT;
		Duty = _Duty;
		GpuUpT = _GpuUpT;
		GpuDownT = _GpuDownT;
	}
}
