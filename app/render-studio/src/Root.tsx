import {Composition} from 'remotion';
import {VidrushVideo, varsayilanProps, VideoProps, normMotion, hesaplaKareler} from './Video';

export const RemotionRoot: React.FC = () => {
  return (
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
  );
};
