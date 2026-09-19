using System.IO;
using System.Linq;
using System.Xml.Serialization;
using Newtonsoft.Json;

namespace LightingModel;

public struct SAVE_EC_LIGHTING_EFFECT_DATA
{
	public byte save_effect;

	public bool bSaved;

	public int MonochromeIndex;

	public int ManualIndex1;

	public int ManualIndex2;

	public int ManualIndex3;

	public int ManualIndex4;

	public int ManualIndex5;

	public int ManualIndex6;

	public int ManualInterval;

	public int BreathingIndex;

	public RGBKB_Color UserDefineColor;

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

	public override int GetHashCode()
	{
		return ((((((((((17 * 23 + save_effect.GetHashCode()) * 23 + bSaved.GetHashCode()) * 23 + MonochromeIndex.GetHashCode()) * 23 + ManualIndex1.GetHashCode()) * 23 + ManualIndex2.GetHashCode()) * 23 + ManualIndex3.GetHashCode()) * 23 + ManualIndex4.GetHashCode()) * 23 + ManualIndex5.GetHashCode()) * 23 + ManualIndex6.GetHashCode()) * 23 + ManualInterval.GetHashCode()) * 23 + BreathingIndex.GetHashCode();
	}

	public static bool operator ==(SAVE_EC_LIGHTING_EFFECT_DATA left, SAVE_EC_LIGHTING_EFFECT_DATA right)
	{
		return left.Equals(right);
	}

	public static bool operator !=(SAVE_EC_LIGHTING_EFFECT_DATA left, SAVE_EC_LIGHTING_EFFECT_DATA right)
	{
		return !(left == right);
	}

	public override string ToString()
	{
		return JsonConvert.SerializeObject(this, Formatting.Indented);
	}
}
