namespace LightingModel;

public struct RGBKB_Event_Data
{
	public RGBKB_EventID event_id;

	public uint envet_data_len;

	public byte[] event_data;
}
