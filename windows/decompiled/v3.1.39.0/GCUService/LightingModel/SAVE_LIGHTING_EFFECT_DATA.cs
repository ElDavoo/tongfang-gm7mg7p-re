using System.IO;
using System.Linq;
using System.Xml.Serialization;
using Newtonsoft.Json;

namespace LightingModel;

public struct SAVE_LIGHTING_EFFECT_DATA
{
	public RGBKB_Mode save_mode;

	public bool bSaved;

	public byte save_effect;

	public byte save_light;

	public byte save_speed;

	public byte save_direction;

	public RGBKB_Color save_layout_color;

	public int save_layout_backgroundcolor;

	public string save_layout_alphbet;

	public RGBKB_PowerStatus save_power_status;

	public override bool Equals(object obj)
	{
		byte[] objectByte = getObjectByte(this);
		return getObjectByte(obj).SequenceEqual(objectByte);
	}

	private byte[] getObjectByte(object model)
	{
		using MemoryStream memoryStream = new MemoryStream();
		new XmlSerializer(model.GetType()).Serialize(memoryStream, model);
		return memoryStream.ToArray();
	}

	public override string ToString()
	{
		return JsonConvert.SerializeObject(this, Formatting.Indented);
	}
}
