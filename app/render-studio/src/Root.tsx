import {Composition} from 'remotion';
import {VidrushVideo, varsayilanProps, VideoProps, normMotion, hesaplaKareler} from './Video';
// ⚠ OPT-IN: VidrushEditorV2 AYRI bir kompozisyon. Mevcut VidrushVideo'nun
// varsayilan davranisi DEGISMEDI; canli hat (pipeline.py) onu cagirmaya devam
// ediyor. V2 yalnizca acikca "VidrushEditorV2" id'siyle cagrilirsa kosar.
import {VidrushEditorV2, editorV2VarsayilanProps, kareHesapla} from './editorv2/EditorV2';
import type {EditorV2Props} from './editorv2/sozlesme';

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Composition
      id="VidrushVideo"
      component={VidrushVideo}
      durationInFrames={150}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={varsayilanProps}
      calculateMetadata={({props}) => {
        const p = props as VideoProps;
        // Crossfade gecisler kare TUKETIR -> toplam sure ortusme kadar KISA olmali
        const {toplam} = hesaplaKareler(p.sahneler, p.fps, normMotion(p.gecis));
        return {
          durationInFrames: Math.max(30, toplam),
          fps: p.fps,
          width: p.genislik,
          height: p.yukseklik,
        };
      }}
    />
    <Composition
      id="VidrushEditorV2"
      component={VidrushEditorV2}
      durationInFrames={90}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={editorV2VarsayilanProps}
      calculateMetadata={({props}) => {
        const p = props as EditorV2Props;
        const kareler = kareHesapla(p.sahneler || [], p.fps || 30);
        const toplam = kareler.reduce((a, b) => a + b, 0);
        return {
          durationInFrames: Math.max(30, toplam),
          fps: p.fps || 30,
          width: p.genislik || 1920,
          height: p.yukseklik || 1080,
        };
      }}
    />
    </>
  );
};
