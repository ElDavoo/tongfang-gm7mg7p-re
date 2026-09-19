namespace MyControlCenter.MyFan.FanTable;

public struct FanTable1p5Buffer
{
	public uint ID;

	public byte UpT;

	public byte DownT;

	public byte Duty;

	public FanTable1p5Buffer(uint _id, byte _UpT, byte _DownT, byte _Duty)
	{
		ID = _id;
		UpT = _UpT;
		DownT = _DownT;
		Duty = _Duty;
	}
}
