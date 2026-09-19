namespace MyControlCenter.MyFan.FanTable;

public struct FanTable2
{
	public FanTable2Buffer[] Table;

	public FanTable2(uint Length)
	{
		Table = new FanTable2Buffer[Length];
		for (uint num = 0u; num < Length; num++)
		{
			Table[num].ID = num;
			Table[num].CpuUpT = 0;
			Table[num].CpuDownT = 0;
			Table[num].Duty = 0;
			Table[num].GpuUpT = 0;
			Table[num].GpuDownT = 0;
		}
	}
}
