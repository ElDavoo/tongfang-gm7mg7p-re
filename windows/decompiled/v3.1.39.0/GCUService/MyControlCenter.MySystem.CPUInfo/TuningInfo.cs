using System.Collections.Generic;
using Intel.Overclocking.SDK.Tuning;

namespace MyControlCenter.MySystem.CPUInfo;

public class TuningInfo
{
	private ITuningLibrary tuning;

	public List<string> TauSupportedValues { get; set; }

	public TuningInfo()
	{
		tuning = TuningLibrary.Instance;
		tuning.Initialize();
	}

	public List<ClientTuningControl> GetAvailableControls()
	{
		if (tuning != null)
		{
			List<ClientTuningControl> availableControls = tuning.GetAvailableControls();
			List<ClientTuningControl> list = new List<ClientTuningControl>();
			{
				foreach (ClientTuningControl item in availableControls)
				{
					if (!item.Enabled)
					{
						continue;
					}
					switch (item.Id)
					{
					case 2u:
						item.Name = "Core Voltage";
						list.Add(item);
						break;
					case 34u:
						item.Name = "Core Voltage Offset";
						list.Add(item);
						break;
					case 47u:
						item.Name = "PL2";
						list.Add(item);
						break;
					case 48u:
						item.Name = "PL1";
						list.Add(item);
						break;
					case 66u:
						item.Name = "Tau";
						list.Add(item);
						TauSupportedValues = item.SupportedValues.ConvertAll((decimal x) => x.ToString());
						break;
					}
				}
				return list;
			}
		}
		return null;
	}

	public ClientTuningControl GetClientTuningControl(uint controlId)
	{
		if (tuning != null)
		{
			return tuning.GetControl(controlId);
		}
		return null;
	}

	public bool Tune(uint id, decimal value, out bool rebootRequired)
	{
		if (!XTUService.IsXtuCLISupport())
		{
			rebootRequired = false;
			return false;
		}
		return tuning.Tune(id, value, out rebootRequired);
	}
}
