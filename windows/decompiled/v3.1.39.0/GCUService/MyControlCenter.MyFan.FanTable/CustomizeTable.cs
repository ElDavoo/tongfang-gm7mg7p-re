namespace MyControlCenter.MyFan.FanTable;

public struct CustomizeTable
{
	public bool Activated;

	public string Name;

	public bool FanControlRespective;

	public string PL1;

	public string PL2;

	public string PL1_dc;

	public string PL2_dc;

	public string DB;

	public string WM;

	public int CpuTemp_DefaultMaxLevel;

	public int GpuTemp_DefaultMaxLevel;

	public FanTable1p5Buffer[] CPU;

	public FanTable1p5Buffer[] GPU;

	public CustomizeTable(uint length, string name)
	{
		Activated = false;
		Name = name;
		FanControlRespective = false;
		PL1 = "NA";
		PL2 = "NA";
		PL1_dc = "NA";
		PL2_dc = "NA";
		DB = "NA";
		WM = "NA";
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
