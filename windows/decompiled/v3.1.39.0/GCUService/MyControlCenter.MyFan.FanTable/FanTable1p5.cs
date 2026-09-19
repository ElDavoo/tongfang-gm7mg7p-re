namespace MyControlCenter.MyFan.FanTable;

public struct FanTable1p5
{
	public bool Activated;

	public string Name;

	public bool FanControlRespective;

	public int CpuTemp_DefaultMaxLevel;

	public int GpuTemp_DefaultMaxLevel;

	public FanTable1p5Buffer[] CPU;

	public FanTable1p5Buffer[] GPU;

	public FanTable1p5(uint length, string name)
	{
		Activated = false;
		Name = name;
		FanControlRespective = false;
		CpuTemp_DefaultMaxLevel = 10;
		GpuTemp_DefaultMaxLevel = 10;
		CPU = new FanTable1p5Buffer[length];
		GPU = new FanTable1p5Buffer[length];
		for (uint num = 0u; num < length; num++)
		{
			CPU[num].ID = num;
			CPU[num].UpT = 0;
			CPU[num].DownT = 0;
			CPU[num].Duty = 0;
			GPU[num].ID = num;
			GPU[num].UpT = 0;
			GPU[num].DownT = 0;
			GPU[num].Duty = 0;
		}
	}
}
