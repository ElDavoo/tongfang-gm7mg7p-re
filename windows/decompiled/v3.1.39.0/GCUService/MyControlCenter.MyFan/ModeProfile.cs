namespace MyControlCenter.MyFan;

public class ModeProfile
{
	public bool Activated;

	public string Name;

	public string CustomizeName;

	public CPU CPU = new CPU();

	public GPU GPU = new GPU();

	public FanSettings FAN = new FanSettings();

	public MemorySettings MEM = new MemorySettings();
}
